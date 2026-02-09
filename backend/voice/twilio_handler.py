"""
Twilio WebSocket handler for voice calls.

Flow:
  Twilio Call -> WebSocket (mu-law 8kHz) -> silence detection ->
  Sarvam STT -> Databricks Agent -> Sarvam TTS -> mu-law chunks -> Twilio playback
"""
import os
import json
import asyncio
import base64
import logging
import time
from typing import Optional, Dict, List

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.voice.audio_utils import (
    is_silence,
    get_audio_duration_ms,
    mulaw_chunks_to_wav,
    wav_to_mulaw,
    SILENCE_DURATION_MS,
    MIN_SPEECH_DURATION_MS,
    MAX_SPEECH_DURATION_MS,
)
from backend.voice import sarvam_voice

logger = logging.getLogger(__name__)

# ── In-memory stores (demo) ───────────────────────────────────────────────
call_transcripts: Dict[str, List[dict]] = {}
call_history: List[dict] = []

GREETING_TEXT = (
    "Namaste! Main hoon Agri Sarthi, aapka kisan mitra. "
    "Aap mujhse fasal ki keemat, mausam, sarkari yojana ya mitti ke baare mein pooch sakte hain. Boliye!"
)
GREETING_LANG = "hi-IN"


# ── SQL Warehouse warmup ──────────────────────────────────────────────────
async def _warmup_sql_warehouse():
    """Send a lightweight query to wake up the serverless SQL warehouse."""
    try:
        import httpx

        host = os.getenv("DATABRICKS_HOST", "")
        token = os.getenv("DATABRICKS_TOKEN", "")
        wid = os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", "")
        if not all([host, token, wid]):
            return
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{host}/api/2.0/sql/statements",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"warehouse_id": wid, "statement": "SELECT 1", "wait_timeout": "30s"},
            )
            logger.info(f"SQL warehouse warmup: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Warehouse warmup error (non-fatal): {e}")


# ── Databricks Agent helper ──────────────────────────────────────────────
async def _invoke_agent(text: str, retry: bool = True) -> str:
    """Call the Databricks AgriSarthi agent endpoint."""
    try:
        import httpx

        await _warmup_sql_warehouse()

        host = os.getenv("DATABRICKS_HOST", "")
        token = os.getenv("DATABRICKS_TOKEN", "")
        endpoint = os.getenv(
            "DATABRICKS_AGENT_ENDPOINT", "agents_agrisarthi-main-agrisarthi_agent"
        )
        url = f"{host}/serving-endpoints/{endpoint}/invocations"
        payload = {"messages": [{"role": "user", "content": text}]}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                messages = data.get("messages", [])
                if messages:
                    for msg in reversed(messages):
                        content = msg.get("content", "")
                        msg_type = msg.get("type", "")
                        if msg_type == "ai" and content and not msg.get("tool_calls"):
                            sorry_phrases = [
                                "couldn't find", "sorry", "not available",
                                "no price data", "unable to find",
                            ]
                            if retry and any(p in content.lower() for p in sorry_phrases):
                                logger.info("Agent said sorry — retrying once...")
                                return await _invoke_agent(text, retry=False)
                            return content

                    last_content = messages[-1].get("content", "")
                    if last_content:
                        return last_content

                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "I'm having trouble responding right now.")
                return data.get("output", "I'm having trouble responding right now.")

            logger.error(f"Agent error {resp.status_code}: {resp.text[:300]}")
            return "Sorry, I am facing a technical issue. Please try again."
    except Exception as e:
        logger.error(f"Agent exception: {e}")
        return "Sorry, I am facing a technical issue. Please try again."


# ── Send audio chunks to Twilio ──────────────────────────────────────────
async def _send_audio_to_twilio(
    websocket: WebSocket, mulaw_base64_chunks: list, stream_sid: str
):
    """Send mu-law audio as base64 chunks over Twilio media stream."""
    for chunk in mulaw_base64_chunks:
        msg = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": chunk},
        }
        try:
            await websocket.send_text(json.dumps(msg))
            await asyncio.sleep(0.02)
        except Exception:
            break


async def _send_clear(websocket: WebSocket, stream_sid: str):
    """Send clear event to stop any queued Twilio audio."""
    try:
        await websocket.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))
    except Exception:
        pass


# ── Process speech -> agent -> TTS ────────────────────────────────────────
async def _process_audio(
    audio_chunks: list,
    call_sid: str,
    websocket: WebSocket,
    stream_sid: str,
):
    """Convert collected audio to text, query agent, synthesize reply."""
    try:
        logger.info(f"Processing {len(audio_chunks)} audio chunks...")

        wav_data = mulaw_chunks_to_wav(audio_chunks)
        if wav_data is None:
            logger.error("Failed to convert audio to WAV")
            return

        transcript, lang = await sarvam_voice.speech_to_text_translate(wav_data)
        if not transcript:
            logger.info("STT returned empty — ignoring")
            return

        logger.info(f"Farmer said ({lang}): {transcript}")

        if call_sid not in call_transcripts:
            call_transcripts[call_sid] = []
        call_transcripts[call_sid].append({
            "role": "farmer", "text": transcript, "language": lang,
        })

        agent_response = await _invoke_agent(transcript)
        logger.info(f"Agent: {agent_response[:150]}")

        call_transcripts[call_sid].append({
            "role": "agent", "text": agent_response, "language": "en-IN",
        })

        tts_lang = lang if lang and lang != "en-IN" else "hi-IN"
        audio_b64 = await sarvam_voice.text_to_speech(agent_response, target_language=tts_lang)
        if not audio_b64:
            logger.error("TTS failed — no audio to send back")
            return

        wav_bytes = base64.b64decode(audio_b64)
        mulaw_chunks = wav_to_mulaw(wav_bytes)
        if not mulaw_chunks:
            logger.error("WAV->mulaw conversion failed")
            return

        logger.info(f"Sending {len(mulaw_chunks)} response chunks to Twilio")
        await _send_clear(websocket, stream_sid)
        await _send_audio_to_twilio(websocket, mulaw_chunks, stream_sid)
        logger.info("Response audio sent")

    except Exception as e:
        logger.error(f"_process_audio error: {e}", exc_info=True)


# ── WebSocket handler ────────────────────────────────────────────────────
async def handle_media_stream(websocket: WebSocket):
    """Main Twilio Media Stream WebSocket handler with silence detection."""
    await websocket.accept()
    logger.info("WebSocket accepted")

    stream_sid: Optional[str] = None
    call_sid: Optional[str] = None
    audio_chunks: list = []
    silence_start: Optional[float] = None
    is_speaking = False
    greeting_sent = False

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event = msg.get("event", "")

            if event == "connected":
                logger.info(f"Twilio stream connected")

            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid", f"call_{int(time.time())}")
                logger.info(f"Call started: sid={call_sid}, stream={stream_sid}")

                call_history.append({
                    "call_sid": call_sid,
                    "direction": "inbound",
                    "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "in-progress",
                })

                if not greeting_sent and stream_sid:
                    greeting_sent = True
                    try:
                        audio_b64 = await sarvam_voice.text_to_speech(
                            GREETING_TEXT, target_language=GREETING_LANG
                        )
                        if audio_b64:
                            wav_bytes = base64.b64decode(audio_b64)
                            mulaw_chunks = wav_to_mulaw(wav_bytes)
                            if mulaw_chunks:
                                await _send_audio_to_twilio(websocket, mulaw_chunks, stream_sid)
                                logger.info("Greeting sent")
                    except Exception as e:
                        logger.error(f"Greeting error: {e}")

            elif event == "media":
                if not stream_sid:
                    continue
                payload = msg.get("media", {}).get("payload", "")
                if not payload:
                    continue

                audio_data = base64.b64decode(payload)
                now = time.time()

                if is_silence(audio_data):
                    if is_speaking:
                        if silence_start is None:
                            silence_start = now
                        elif (now - silence_start) * 1000 >= SILENCE_DURATION_MS:
                            duration_ms = get_audio_duration_ms(audio_chunks)
                            if duration_ms >= MIN_SPEECH_DURATION_MS:
                                asyncio.create_task(
                                    _process_audio(
                                        list(audio_chunks), call_sid or "unknown",
                                        websocket, stream_sid,
                                    )
                                )
                            audio_chunks = []
                            is_speaking = False
                            silence_start = None
                else:
                    is_speaking = True
                    silence_start = None
                    audio_chunks.append(audio_data)

                    if get_audio_duration_ms(audio_chunks) >= MAX_SPEECH_DURATION_MS:
                        asyncio.create_task(
                            _process_audio(
                                list(audio_chunks), call_sid or "unknown",
                                websocket, stream_sid,
                            )
                        )
                        audio_chunks = []
                        is_speaking = False
                        silence_start = None

            elif event == "stop":
                logger.info(f"Call ended: {call_sid}")
                for rec in call_history:
                    if rec.get("call_sid") == call_sid:
                        rec["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        rec["status"] = "completed"
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {call_sid}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        for rec in call_history:
            if rec.get("call_sid") == call_sid and rec["status"] == "in-progress":
                rec["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                rec["status"] = "completed"


# ── TwiML for incoming calls ────────────────────────────────────────────
def generate_incoming_call_twiml(ws_url: str) -> str:
    """Return TwiML XML that connects the call to our WebSocket."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="service" value="agrisarthi" />
        </Stream>
    </Connect>
    <Pause length="60"/>
</Response>"""
