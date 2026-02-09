"""
AgriSarthi WhatsApp Bot — Databricks Agent Client

Calls the Databricks Model Serving endpoint (same backend as Web + Voice).
"""
import os
import requests
from whatsapp.config.logging import logger

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://dbc-54e28175-826c.cloud.databricks.com")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_ENDPOINT = os.getenv("DATABRICKS_ENDPOINT", "agents_agrisarthi-main-agrisarthi_agent")


def invoke_agent(user_message: str) -> str:
    """Send a message to the Databricks AgriSarthi agent and return the response."""
    url = f"{DATABRICKS_HOST}/serving-endpoints/{DATABRICKS_ENDPOINT}/invocations"
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"messages": [{"role": "user", "content": user_message}]}

    try:
        logger.info(f"Invoking Databricks agent: {user_message[:80]}...")
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Extract the final AI message
        messages = data.get("messages", [])
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("type") == "ai" and msg.get("content"):
                    return msg["content"]

        # Fallback formats
        if "output" in data:
            output = data["output"]
            if isinstance(output, str):
                return output
            if isinstance(output, dict):
                return output.get("content", str(output))

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        logger.warning(f"Unexpected response format: {list(data.keys())}")
        return "I apologize, I'm having trouble processing your request right now. Please try again."

    except requests.exceptions.Timeout:
        logger.error("Databricks agent request timed out")
        return "I'm sorry, the request took too long. Please try again in a moment."
    except requests.exceptions.RequestException as e:
        logger.error(f"Databricks agent request failed: {e}")
        return "I'm sorry, I'm facing a technical issue right now. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error invoking Databricks agent: {e}", exc_info=True)
        return "I apologize, an unexpected error occurred. Please try again."
