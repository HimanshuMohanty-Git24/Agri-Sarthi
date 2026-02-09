"""
Audio utilities for Twilio <-> Sarvam AI conversion.
Handles mu-law (Twilio) <-> WAV (Sarvam AI) transcoding.
"""
import audioop
import wave
import io
import base64
import logging

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────
SILENCE_THRESHOLD = 1000       # RMS threshold for silence detection
SAMPLES_PER_MS = 8             # 8kHz -> 8 samples per ms
MIN_SPEECH_DURATION_MS = 800   # Min speech before processing
MAX_SPEECH_DURATION_MS = 15000 # Force-process after 15s
SILENCE_DURATION_MS = 1200     # 1.2s silence -> end of utterance
MULAW_CHUNK_SIZE = 640         # 640 bytes = 80ms of mu-law audio at 8kHz


def is_silence(audio_data: bytes) -> bool:
    """Check if a mu-law audio chunk is silence."""
    try:
        pcm_data = audioop.ulaw2lin(audio_data, 2)
        rms = audioop.rms(pcm_data, 2)
        return rms < SILENCE_THRESHOLD
    except Exception as e:
        logger.error(f"Silence check error: {e}")
        return True


def get_audio_duration_ms(audio_chunks: list[bytes]) -> float:
    """Calculate duration in ms from mu-law audio chunks (8kHz, 1 byte/sample)."""
    total_bytes = sum(len(c) for c in audio_chunks)
    return total_bytes / SAMPLES_PER_MS


def mulaw_chunks_to_wav(audio_chunks: list[bytes], target_rate: int = 16000) -> bytes:
    """Convert mu-law audio chunks (8kHz) to WAV bytes at target_rate for Sarvam AI."""
    try:
        pcm_data = b"".join(audioop.ulaw2lin(chunk, 2) for chunk in audio_chunks)
        if target_rate != 8000:
            pcm_data, _ = audioop.ratecv(pcm_data, 2, 1, 8000, target_rate, None)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"mulaw->WAV conversion error: {e}")
        raise


def wav_to_mulaw(wav_data: bytes) -> list[str]:
    """
    Convert WAV audio to base64-encoded mu-law chunks (8kHz, mono) for Twilio.
    Returns a list of base64-encoded strings, each representing a 640-byte
    mu-law chunk (~80ms of audio).
    """
    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            pcm_data = wf.readframes(wf.getnframes())

        if n_channels == 2:
            pcm_data = audioop.tomono(pcm_data, sampwidth, 1, 1)
        if sampwidth != 2:
            pcm_data = audioop.lin2lin(pcm_data, sampwidth, 2)
        if framerate != 8000:
            pcm_data, _ = audioop.ratecv(pcm_data, 2, 1, framerate, 8000, None)

        mulaw_data = audioop.lin2ulaw(pcm_data, 2)

        chunks = []
        for i in range(0, len(mulaw_data), MULAW_CHUNK_SIZE):
            chunk = mulaw_data[i : i + MULAW_CHUNK_SIZE]
            chunks.append(base64.b64encode(chunk).decode("ascii"))

        return chunks
    except Exception as e:
        logger.error(f"WAV->mulaw conversion error: {e}")
        return []
