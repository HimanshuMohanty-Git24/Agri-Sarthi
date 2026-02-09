"""
AgriSarthi — Databricks Agent Client
Handles communication with Databricks Model Serving endpoint.
"""
import os
import json
import time
import asyncio
import httpx
from typing import Optional, Dict, Any, AsyncGenerator


class DatabricksAgentClient:
    """Client for calling AgriSarthi agent on Databricks Model Serving."""

    def __init__(self):
        self.host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
        self.token = os.getenv("DATABRICKS_TOKEN", "")
        self.endpoint_name = os.getenv(
            "DATABRICKS_AGENT_ENDPOINT",
            "agents_agrisarthi-main-agrisarthi_agent",
        )

        if not self.host or not self.token:
            raise ValueError(
                "DATABRICKS_HOST and DATABRICKS_TOKEN must be set. "
                "Get these from your Databricks workspace."
            )

        self.endpoint_url = f"{self.host}/serving-endpoints/{self.endpoint_name}/invocations"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def invoke(self, user_message: str, session_id: str = "default") -> str:
        """Invoke the AgriSarthi agent endpoint."""
        payload = {
            "messages": [{"role": "user", "content": user_message}],
            "custom_inputs": {"session_id": session_id},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.endpoint_url, json=payload, headers=self.headers
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                if messages:
                    return messages[-1].get("content", "I couldn't process your request.")
                return result.get("output", "No response received.")
            else:
                raise Exception(
                    f"Databricks endpoint error: {response.status_code} — {response.text}"
                )

    async def invoke_streaming(
        self, user_message: str, session_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        Invoke agent and simulate streaming by yielding word chunks.
        (Agent endpoints don't support native SSE streaming.)
        """
        try:
            full_response = await self.invoke(user_message, session_id)

            if not full_response:
                yield "I couldn't process your request. Please try again."
                return

            words = full_response.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i : i + 3])
                if i + 3 < len(words):
                    chunk += " "
                yield chunk
                await asyncio.sleep(0.03)

        except Exception as e:
            print(f"[CLIENT] invoke_streaming error: {e}")
            yield f"Sorry, I encountered an error: {str(e)}"

    async def log_conversation(
        self,
        session_id: str,
        farmer_id: str,
        channel: str,
        user_message: str,
        agent_response: str,
        language: str = "en-IN",
        response_time_ms: float = 0,
    ) -> None:
        """Log conversation to Delta table via SQL Statement API."""
        try:
            sql_url = f"{self.host}/api/2.0/sql/statements"
            sql_payload = {
                "warehouse_id": os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", ""),
                "statement": f"""
                    INSERT INTO agrisarthi.main.conversation_logs
                    (session_id, farmer_id, channel, user_message, agent_response,
                     language, response_time_ms)
                    VALUES ('{session_id}', '{farmer_id}', '{channel}',
                            '{user_message.replace("'", "''")}',
                            '{agent_response[:500].replace("'", "''")}',
                            '{language}', {response_time_ms})
                """,
                "wait_timeout": "10s",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(sql_url, json=sql_payload, headers=self.headers)

        except Exception as e:
            print(f"[CLIENT] Failed to log conversation: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Check if the Databricks endpoint is healthy."""
        import requests

        try:
            url = f"{self.host}/api/2.0/serving-endpoints/{self.endpoint_name}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", {}).get("ready", "UNKNOWN")
                return {"status": "healthy", "endpoint_state": state}
            return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# ─── Lakebase Session Store ─────────────────────────────────────────

class LakebaseSessionStore:
    """
    Session store using Databricks Lakebase (Serverless PostgreSQL).
    Stores conversation history and farmer context.
    """

    def __init__(self):
        self.host = os.getenv("LAKEBASE_HOST", "")
        self.port = int(os.getenv("LAKEBASE_PORT", "5432"))
        self.dbname = os.getenv("LAKEBASE_DB", "agrisarthi")
        self.user = os.getenv("LAKEBASE_USER", "")
        self.password = os.getenv("LAKEBASE_PASSWORD", "")
        self._pool = None

    async def initialize(self):
        """Initialize connection pool and create tables."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.dbname,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
                ssl="require",
            )

            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        farmer_id TEXT,
                        channel TEXT DEFAULT 'web',
                        language TEXT DEFAULT 'en-IN',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        last_active TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT REFERENCES sessions(session_id),
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, created_at)
                """)

            print("[CLIENT] Lakebase session store initialized")

        except ImportError:
            print("[CLIENT] asyncpg not installed — Lakebase disabled")
            self._pool = None
        except Exception as e:
            print(f"[CLIENT] Lakebase connection failed: {e}")
            self._pool = None

    async def get_or_create_session(
        self, session_id: str, farmer_id: str = "", channel: str = "web"
    ) -> Dict[str, Any]:
        """Get existing session or create new one."""
        if not self._pool:
            return {"session_id": session_id, "history": []}

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, farmer_id, channel)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id) DO UPDATE SET last_active = NOW()
            """,
                session_id,
                farmer_id,
                channel,
            )

            rows = await conn.fetch(
                """
                SELECT role, content FROM messages
                WHERE session_id = $1
                ORDER BY created_at DESC LIMIT 10
            """,
                session_id,
            )

            history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
            return {"session_id": session_id, "history": history}

    async def add_message(
        self, session_id: str, role: str, content: str, metadata: dict = None
    ) -> None:
        """Add a message to the session."""
        if not self._pool:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata)
                VALUES ($1, $2, $3, $4)
            """,
                session_id,
                role,
                content,
                json.dumps(metadata or {}),
            )

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
