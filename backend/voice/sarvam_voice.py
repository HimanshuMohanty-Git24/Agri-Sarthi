"""
Async Sarvam AI service for voice calls.
Handles: STT (speech-to-text-translate), Translation, TTS.
"""
import os
import base64
import tempfile
import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_API_BASE = "https://api.sarvam.ai"


async def speech_to_text_translate(wav_data: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Send WAV audio to Sarvam speech-to-text-translate.
    Returns (english_text, detected_language_code) or (None, None).
    """
    tmp_path = None
    fh = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_data)
            tmp_path = tmp.name

        fh = open(tmp_path, "rb")
        files = {"file": ("audio.wav", fh, "audio/wav")}
        data = {"model": "saaras:v2.5"}
        headers = {"api-subscription-key": SARVAM_API_KEY}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SARVAM_API_BASE}/speech-to-text-translate",
                files=files,
                data=data,
                headers=headers,
            )
            if resp.status_code == 200:
                result = resp.json()
                transcript = result.get("transcript", "").strip()
                lang = result.get("language_code", "en-IN")
                if not transcript:
                    return None, None
                logger.info(f"STT: '{transcript}' (lang={lang})")
                return transcript, lang
            else:
                logger.error(f"STT error {resp.status_code}: {resp.text[:200]}")
                return None, None
    except Exception as e:
        logger.error(f"STT exception: {e}")
        return None, None
    finally:
        if fh:
            try:
                fh.close()
            except Exception:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


async def translate_text(
    text: str,
    target_language: str,
    source_language: str = "en-IN",
) -> str:
    """Translate text via Sarvam AI. Returns original on failure."""
    if source_language == target_language:
        return text
    try:
        payload = {
            "input": text,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1",
            "enable_preprocessing": True,
        }
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": SARVAM_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{SARVAM_API_BASE}/translate", json=payload, headers=headers
            )
            if resp.status_code == 200:
                return resp.json().get("translated_text", text).strip()
            logger.error(f"Translate error {resp.status_code}: {resp.text[:200]}")
            return text
    except Exception as e:
        logger.error(f"Translate exception: {e}")
        return text


async def text_to_speech(
    text: str,
    target_language: str = "en-IN",
    speaker: str = "anushka",
) -> Optional[str]:
    """
    Convert text -> speech via Sarvam AI.
    Translates first if non-English, then synthesises.
    Returns base64-encoded WAV audio or None.
    """
    try:
        tts_text = text[:500]

        if target_language != "en-IN":
            translated = await translate_text(tts_text, target_language, "en-IN")
            if translated:
                tts_text = translated[:500]

        payload = {
            "inputs": [tts_text],
            "target_language_code": target_language,
            "speaker": speaker,
            "model": "bulbul:v2",
        }
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": SARVAM_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{SARVAM_API_BASE}/text-to-speech", json=payload, headers=headers
            )
            if resp.status_code == 200:
                audios = resp.json().get("audios", [])
                if audios:
                    base64.b64decode(audios[0])  # validate
                    return audios[0]
                logger.error("TTS returned no audio")
                return None
            logger.error(f"TTS error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"TTS exception: {e}")
        return None
