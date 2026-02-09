"""
Sarvam AI integration for WhatsApp Bot.
Handles: language detection, translation, TTS, STT.
"""
import os
import requests
import base64
import tempfile
from langdetect import detect
from whatsapp.config.logging import logger

SARVAM_API_KEY = os.getenv("SARVAM_AI_API_KEY")
SARVAM_API_BASE = "https://api.sarvam.ai"

# langdetect code -> Sarvam language code mapping
LANGUAGE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "or": "od-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
}


def detect_language(text: str) -> str:
    """Detect language using langdetect, return Sarvam code."""
    try:
        lang_code = detect(text)
        return LANGUAGE_MAP.get(lang_code, "en-IN")
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return "en-IN"


def detect_language_sarvam(text: str) -> str:
    """Detect language using Sarvam AI API."""
    if not SARVAM_API_KEY:
        return detect_language(text)

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    payload = {"text": text}

    try:
        response = requests.post(f"{SARVAM_API_BASE}/detect-language", headers=headers, json=payload)
        response.raise_for_status()
        detected_lang = response.json().get("language_code", "en-IN")
        logger.info(f"Detected language: {detected_lang}")
        return detected_lang
    except Exception as e:
        logger.error(f"Sarvam language detection failed: {e}")
        return detect_language(text)


def translate_text(text: str, target_language: str, source_language: str = None) -> str:
    """Translate text using Sarvam AI."""
    if not SARVAM_API_KEY:
        logger.error("SARVAM_AI_API_KEY not set.")
        return text

    if source_language is None or source_language == "auto":
        source_language = detect_language_sarvam(text)

    if source_language == target_language:
        return text

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "input": text,
        "source_language_code": source_language,
        "target_language_code": target_language,
        "speaker_gender": "Male",
        "mode": "formal",
        "enable_preprocessing": True,
        "output_script": None,
        "numerals_format": "international",
    }

    try:
        response = requests.post(f"{SARVAM_API_BASE}/translate", headers=headers, json=payload)
        response.raise_for_status()
        translated_text = response.json().get("translated_text", text)
        logger.info(f"Translation: {source_language} -> {target_language}")
        return translated_text
    except Exception as e:
        logger.error(f"Sarvam translation failed: {e}")
        return text


def text_to_speech(
    text: str, language_code: str = "en-IN", speaker: str = "meera", model: str = "bulbul:v1"
) -> str | None:
    """Convert text to speech, returns path to WAV file or None."""
    if not SARVAM_API_KEY:
        logger.error("SARVAM_AI_API_KEY not set.")
        return None

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": speaker,
        "pitch": 0.0,
        "pace": 1.0,
        "loudness": 1.0,
        "speech_sample_rate": 22050,
        "enable_preprocessing": False,
        "model": model,
    }

    try:
        response = requests.post(f"{SARVAM_API_BASE}/text-to-speech", headers=headers, json=payload)
        response.raise_for_status()
        audio_base64_list = response.json().get("audios", [])

        if not audio_base64_list:
            logger.error("TTS API returned no audio data.")
            return None

        audio_data = base64.b64decode(audio_base64_list[0])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data)
            logger.info(f"TTS audio saved: {tmp_file.name}")
            return tmp_file.name
    except Exception as e:
        logger.error(f"Sarvam TTS failed: {e}")
        return None


def speech_to_text_translate(audio_file_path: str) -> str | None:
    """Transcribe speech and translate to English using Sarvam AI."""
    if not SARVAM_API_KEY:
        logger.error("SARVAM_AI_API_KEY not set.")
        return None

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}

    try:
        with open(audio_file_path, "rb") as audio_file:
            files = {"file": (audio_file_path, audio_file, "audio/wav")}
            response = requests.post(
                f"{SARVAM_API_BASE}/speech-to-text-translate", headers=headers, files=files
            )
            response.raise_for_status()
            transcript = response.json().get("transcript", "")
            logger.info("Speech-to-text translation successful")
            return transcript
    except Exception as e:
        logger.error(f"Sarvam STT failed: {e}")
        return None
