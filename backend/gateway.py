"""
AgriSarthi — FastAPI Gateway
Connects all channels (Web, Voice, WhatsApp) to Databricks Model Serving.

Run from project root:
    uvicorn backend.gateway:app --reload --host 0.0.0.0 --port 8000
"""
import os
import json
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from backend.client import DatabricksAgentClient, LakebaseSessionStore

# ─── Voice imports ──────────────────────────────────────────────────
voice_routes_enabled = False
try:
    from backend.voice.views import (
        voice_websocket_handler,
        handle_incoming_call,
        create_outbound_call,
        get_call_history,
        get_call_transcript,
    )
    from backend.voice.models import VoiceCallCreate
    voice_routes_enabled = True
    print("[BACKEND] Voice agent imports successful")
except Exception as e:
    print(f"[BACKEND] Voice routes disabled: {e}")

# ─── Initialize clients ────────────────────────────────────────────
agent_client = None
session_store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global agent_client, session_store

    try:
        agent_client = DatabricksAgentClient()
        health = agent_client.health_check()
        print(f"[BACKEND] Databricks agent client: {health}")
    except Exception as e:
        print(f"[BACKEND] Databricks agent client failed: {e}")

    try:
        session_store = LakebaseSessionStore()
        await session_store.initialize()
    except Exception as e:
        print(f"[BACKEND] Lakebase session store failed: {e}")
        session_store = None

    yield

    if session_store:
        await session_store.close()


# ─── FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title="AgriSarthi — Databricks-Powered Farming Assistant",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    language: str = "en-IN"
    channel: str = "web"


# ─── Chat Endpoint ──────────────────────────────────────────────────

async def stream_generator(
    thread_id: str, user_message: str, language: str = "en-IN", channel: str = "web"
):
    """Generate streaming response from Databricks agent."""
    start_time = time.time()
    full_response = ""

    try:
        if agent_client:
            async for chunk in agent_client.invoke_streaming(user_message, thread_id):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        else:
            error_msg = "Agent not available. Please configure DATABRICKS_HOST and DATABRICKS_TOKEN."
            yield f"data: {json.dumps({'content': error_msg})}\n\n"

        yield "data: [DONE]\n\n"

        elapsed_ms = (time.time() - start_time) * 1000
        if agent_client and full_response:
            await agent_client.log_conversation(
                session_id=thread_id,
                farmer_id=thread_id,
                channel=channel,
                user_message=user_message,
                agent_response=full_response,
                language=language,
                response_time_ms=elapsed_ms,
            )

        if session_store:
            await session_store.add_message(thread_id, "user", user_message)
            await session_store.add_message(thread_id, "assistant", full_response)

    except Exception as e:
        print(f"[BACKEND] Error in stream_generator: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint — streams response from Databricks agent."""
    return StreamingResponse(
        stream_generator(request.thread_id, request.message, request.language, request.channel),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


@app.post("/chat/sync")
async def chat_sync_endpoint(request: ChatRequest):
    """Synchronous chat endpoint — returns full response at once."""
    start_time = time.time()

    try:
        if agent_client:
            response = await agent_client.invoke(request.message, request.thread_id)
        else:
            response = "Agent not available. Configure Databricks connection."

        elapsed_ms = (time.time() - start_time) * 1000

        if agent_client:
            await agent_client.log_conversation(
                session_id=request.thread_id,
                farmer_id=request.thread_id,
                channel=request.channel,
                user_message=request.message,
                agent_response=response,
                language=request.language,
                response_time_ms=elapsed_ms,
            )

        return {
            "response": response,
            "session_id": request.thread_id,
            "response_time_ms": round(elapsed_ms, 2),
        }

    except Exception as e:
        return {"error": str(e), "response": "Sorry, an error occurred. Please try again."}


# ─── Sarvam AI Proxy (avoids CORS issues from browser) ─────────────

import httpx

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_API_BASE = "https://api.sarvam.ai"


class TranslateRequest(BaseModel):
    input: str
    source_language_code: str = "en-IN"
    target_language_code: str = "hi-IN"
    model: str = "mayura:v1"
    enable_preprocessing: bool = True


class TTSRequest(BaseModel):
    text: str
    target_language_code: str = "en-IN"
    speaker: str = "anushka"
    pitch: float = 0
    pace: float = 1
    loudness: float = 1
    speech_sample_rate: int = 22050
    enable_preprocessing: bool = True
    model: str = "bulbul:v2"


@app.post("/api/translate")
async def translate_proxy(request: TranslateRequest):
    """Proxy translation requests to Sarvam AI to avoid CORS issues."""
    if not SARVAM_API_KEY:
        return {"error": "Sarvam API key not configured"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SARVAM_API_BASE}/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json=request.dict(),
        )
        return resp.json()


@app.post("/api/tts")
async def tts_proxy(request: TTSRequest):
    """Proxy TTS requests to Sarvam AI to avoid CORS issues."""
    if not SARVAM_API_KEY:
        return {"error": "Sarvam API key not configured"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SARVAM_API_BASE}/text-to-speech",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json=request.dict(),
        )
        return resp.json()


# ─── Voice Endpoints ────────────────────────────────────────────────

@app.websocket("/ws/voice-stream")
async def voice_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Twilio voice streaming."""
    if not voice_routes_enabled:
        await websocket.close(code=1000, reason="Voice service unavailable")
        return
    try:
        await voice_websocket_handler(websocket)
    except Exception as e:
        print(f"[BACKEND] WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass


@app.post("/voice/incoming-call", status_code=200)
async def incoming_call_endpoint(request: Request):
    """Handle incoming Twilio voice calls."""
    if not voice_routes_enabled:
        return Response(
            content="<Response><Say>Voice agent is currently unavailable.</Say></Response>",
            media_type="text/xml",
        )
    try:
        return await handle_incoming_call(request)
    except Exception:
        return Response(
            content="<Response><Say>Technical error occurred</Say></Response>",
            media_type="text/xml",
        )


@app.post("/voice/outbound-call")
async def outbound_call_endpoint(call_request: dict):
    """Create outbound call to farmer."""
    if not voice_routes_enabled:
        return {"error": "Voice service not available"}
    try:
        call_obj = VoiceCallCreate(**call_request)
        return await create_outbound_call(call_obj)
    except Exception as e:
        return {"error": str(e)}


@app.get("/voice/call-history")
async def call_history_endpoint():
    if not voice_routes_enabled:
        return {"error": "Voice service not available", "calls": []}
    return await get_call_history()


@app.get("/voice/call-transcript/{call_id}")
async def call_transcript_endpoint(call_id: str):
    if not voice_routes_enabled:
        return {"error": "Voice service not available", "transcript": []}
    return await get_call_transcript(call_id)


# ─── Health & Status ────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {
        "service": "AgriSarthi — Databricks-Powered Farming Assistant",
        "status": "active",
        "version": "2.0.0",
        "channels": ["Web Chat", "Voice (Twilio)", "WhatsApp"],
        "powered_by": "Databricks Mosaic AI + Model Serving",
    }


@app.get("/health")
def health_check():
    databricks_status = "unknown"
    if agent_client:
        health = agent_client.health_check()
        databricks_status = health.get("status", "unknown")

    return {
        "status": "healthy",
        "databricks_agent": databricks_status,
        "voice_agent": "enabled" if voice_routes_enabled else "disabled",
        "session_store": "lakebase" if session_store and session_store._pool else "in-memory",
        "version": "2.0.0",
    }


@app.get("/test")
def test_endpoint():
    """Quick connectivity check for frontend."""
    return {
        "status": "ok",
        "message": "AgriSarthi backend is running",
        "agent_connected": agent_client is not None,
    }
