"""WhatsApp API wrapper using WPPConnect."""
import base64
import logging
import os
from typing import Dict

import requests

logger = logging.getLogger(__name__)


class WhatsAppConnection:
    def __init__(self):
        self.base_url = os.getenv("WPPCONNECT_BASE_URL", "").rstrip("/")
        self.session = os.getenv("WPPCONNECT_SESSION_NAME")
        self.secret_key = os.getenv("WPPCONNECT_SECRET_KEY")
        self.token = os.getenv("WPPCONNECT_TOKEN")

    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise ValueError("WPPCONNECT_TOKEN is not set in environment variables.")
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }


def send_message(message: str, phone_number: str) -> Dict:
    """Send a WhatsApp text message."""
    if not phone_number:
        raise ValueError("Missing phone_number")

    conn = WhatsAppConnection()
    url = f"{conn.base_url}/api/{conn.session}/send-message"
    headers = conn._get_headers()
    data = {"phone": phone_number, "message": message}

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message: {e}")
        raise


def send_voice(audio_path: str, phone_number: str) -> Dict:
    """Send a WhatsApp voice message."""
    if not phone_number:
        raise ValueError("Missing phone_number")
    if not audio_path:
        raise ValueError("Missing audio file path")

    try:
        with open(audio_path, "rb") as audio_file:
            base64_audio = base64.b64encode(audio_file.read()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error reading audio file: {e}")

    conn = WhatsAppConnection()
    url = f"{conn.base_url}/api/{conn.session}/send-voice-base64"
    headers = conn._get_headers()
    data = {
        "phone": phone_number,
        "isGroup": False,
        "base64Ptt": f"data:audio/mpeg;base64,{base64_audio}",
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending voice message: {e}")
        raise
