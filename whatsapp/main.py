"""
AgriSarthi WhatsApp Bot — Webhook Handler

Receives WhatsApp messages via WPPConnect, translates, queries
the Databricks agent, translates back, and replies.

Run from project root:
    uvicorn whatsapp.main:app --reload --host 0.0.0.0 --port 8001
"""
import asyncio
import base64
import os
import tempfile
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

load_dotenv()

from whatsapp.databricks_client import invoke_agent
from whatsapp.config.logging import logger
from whatsapp.wppconnect.api import send_message, send_voice
from whatsapp.sarvam import detect_language, translate_text, text_to_speech

WAIT_TIME = os.getenv("WAIT_TIME", 2)

# Groq client for audio transcription (optional — Groq Whisper)
try:
    from whatsapp.config.config import setup_groq_client
    GROQ_CLIENT = setup_groq_client()
except Exception:
    GROQ_CLIENT = None
    logger.warning("Groq client not available — voice transcription disabled")

message_buffers = defaultdict(list)
processing_tasks = {}


# ─── Pydantic Models ────────────────────────────────────────────────
class Sender(BaseModel):
    id: str


class WebhookData(BaseModel):
    event: str
    session: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    isNewMsg: Optional[bool] = None
    sender: Optional[Sender] = None


# ─── Audio Transcription ────────────────────────────────────────────
async def transcribe_base64_audio(base64_audio: str) -> str:
    """Transcribe audio from base64 data using Groq Whisper."""
    if not GROQ_CLIENT:
        raise RuntimeError("Groq client not available for audio transcription")
    try:
        audio_data = base64.b64decode(base64_audio)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name

        with open(tmp_file_path, "rb") as audio_file:
            transcription = GROQ_CLIENT.audio.transcriptions.create(
                model="whisper-large-v3", file=audio_file
            )
        os.unlink(tmp_file_path)
        return transcription.text
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}")
        if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        raise


# ─── Message Processing ─────────────────────────────────────────────
async def process_aggregated_messages(sender_id: str, is_voice_message: bool):
    """Process messages after waiting period."""
    try:
        await asyncio.sleep(int(WAIT_TIME))
        messages = message_buffers.get(sender_id, [])
        if not messages:
            return

        combined_message = " ".join(messages)
        del message_buffers[sender_id]

        phone_number = sender_id.split("@")[0]
        logger.info(f"Processing for {phone_number}: '{combined_message}' (Voice: {is_voice_message})")

        # 1. Detect language
        original_lang = detect_language(combined_message)
        logger.info(f"Detected language: {original_lang}")

        # 2. Translate to English for agent if needed
        input_for_agent = (
            translate_text(combined_message, target_language="en-IN", source_language=original_lang)
            if original_lang != "en-IN"
            else combined_message
        )

        # 3. Invoke Databricks agent
        final_response = invoke_agent(input_for_agent)
        logger.info(f"Agent response (English): '{final_response}'")

        # 4. Translate back
        final_response_translated = (
            translate_text(final_response, target_language=original_lang, source_language="en-IN")
            if original_lang != "en-IN"
            else final_response
        )

        # 5. Send response
        if is_voice_message:
            audio_path = text_to_speech(final_response_translated, language_code=original_lang)
            if audio_path:
                send_voice(audio_path, phone_number)
                os.unlink(audio_path)
                logger.info(f"Sent TTS voice reply to {phone_number}")
            else:
                send_message(final_response_translated, phone_number)
                logger.error(f"TTS failed, sent text fallback to {phone_number}")
        else:
            send_message(final_response_translated, phone_number)
            logger.info(f"Sent text reply to {phone_number}")

    except Exception as e:
        logger.error(f"Error in process_aggregated_messages: {str(e)}", exc_info=True)
        send_message(
            "Sorry, an internal error occurred. Please try again.",
            sender_id.split("@")[0],
        )
    finally:
        if sender_id in processing_tasks:
            del processing_tasks[sender_id]


# ─── FastAPI App ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgriSarthi WhatsApp Bot starting up...")
    yield
    logger.info("AgriSarthi WhatsApp Bot shutting down.")


app = FastAPI(title="AgriSarthi WhatsApp Bot", lifespan=lifespan)


@app.post("/webhook")
async def webhook_handler(data: Dict[str, Any]):
    try:
        parsed_data = WebhookData(**data)

        if not (
            parsed_data.event == "onmessage"
            and parsed_data.isNewMsg
            and parsed_data.type in ["chat", "ptt"]
            and parsed_data.sender
        ):
            return {"status": "skipped", "reason": "Not a new user message event"}

        sender_id = parsed_data.sender.id
        is_voice = parsed_data.type == "ptt"
        message_text = ""

        if is_voice:
            message_text = await transcribe_base64_audio(parsed_data.body)
            logger.info(f"Transcribed from {sender_id}: '{message_text}'")
        else:
            message_text = parsed_data.body

        if not message_text or not message_text.strip():
            return {"status": "skipped", "reason": "Empty message"}

        message_buffers[sender_id].append(message_text)
        if sender_id not in processing_tasks:
            task = asyncio.create_task(process_aggregated_messages(sender_id, is_voice))
            processing_tasks[sender_id] = task

        return {"status": "aggregating"}

    except ValidationError as e:
        logger.debug(f"Skipping non-message event: {e.errors()}")
        return {"status": "skipped", "reason": "Non-message event"}
    except Exception as e:
        logger.error(f"Webhook handler error: {str(e)}", exc_info=True)
        return {"status": "error", "detail": "Internal server error"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "whatsapp-bot"}
