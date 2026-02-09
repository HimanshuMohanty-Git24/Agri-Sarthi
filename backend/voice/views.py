"""
Voice views — public API used by gateway.py.

Exports:
  - voice_websocket_handler
  - handle_incoming_call
  - create_outbound_call
  - get_call_history
  - get_call_transcript
"""
import os
import logging
from typing import Optional

from fastapi import WebSocket, Request
from fastapi.responses import Response, JSONResponse

from backend.voice.twilio_handler import (
    handle_media_stream,
    generate_incoming_call_twiml,
    call_history,
    call_transcripts,
)
from backend.voice.models import VoiceCallCreate

logger = logging.getLogger(__name__)


async def voice_websocket_handler(websocket: WebSocket):
    """Handle Twilio MediaStream WebSocket."""
    await handle_media_stream(websocket)


async def handle_incoming_call(request: Request) -> Response:
    """Twilio POST webhook — returns TwiML connecting call to WebSocket."""
    host = request.headers.get("host", "localhost:8000")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    scheme = "wss" if proto == "https" else "ws"
    ws_url = f"{scheme}://{host}/ws/voice-stream"

    logger.info(f"TwiML WebSocket URL: {ws_url}")
    twiml = generate_incoming_call_twiml(ws_url)
    return Response(content=twiml, media_type="application/xml")


async def create_outbound_call(call_data: VoiceCallCreate) -> dict:
    """Create an outbound call via Twilio REST API."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = call_data.from_number or os.getenv("TWILIO_PHONE_NUMBER", "")

    if not all([account_sid, auth_token, from_number]):
        return {"error": "Twilio credentials not configured"}

    try:
        import httpx

        webhook_url = call_data.webhook_url
        if not webhook_url:
            return {"error": "webhook_url required for outbound calls"}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
        data = {"To": call_data.to, "From": from_number, "Url": webhook_url}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=data, auth=(account_sid, auth_token))
            if resp.status_code in (200, 201):
                result = resp.json()
                call_history.append({
                    "call_sid": result.get("sid", ""),
                    "direction": "outbound",
                    "from_number": from_number,
                    "to_number": call_data.to,
                    "start_time": result.get("date_created", ""),
                    "status": result.get("status", "queued"),
                })
                return {"call_sid": result.get("sid"), "status": result.get("status")}
            return {"error": f"Twilio API error {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        logger.error(f"Outbound call error: {e}")
        return {"error": str(e)}


async def get_call_history() -> list:
    """Return all call records (in-memory)."""
    return call_history


async def get_call_transcript(call_id: str) -> list:
    """Return transcript entries for a call."""
    return call_transcripts.get(call_id, [])
