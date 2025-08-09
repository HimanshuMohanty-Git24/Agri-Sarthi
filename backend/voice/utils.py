import audioop
import wave
import io
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

def is_silence(audio_data: bytes, threshold: int = 300) -> bool:
    """Check if audio chunk is silence"""
    try:
        rms = audioop.rms(audio_data, 1)
        return rms < threshold
    except Exception:
        return True

def get_audio_duration_ms(audio_chunks: List[bytes], sample_rate: int = 8000) -> float:
    """Calculate total duration of audio chunks in milliseconds"""
    try:
        total_samples = sum(len(chunk) for chunk in audio_chunks)
        duration_seconds = total_samples / sample_rate
        return duration_seconds * 1000
    except Exception:
        return 0.0

def convert_mulaw_to_wav(mulaw_data: bytes) -> bytes:
    """Convert μ-law encoded audio to WAV format"""
    try:
        # Convert μ-law to linear PCM
        linear_data = audioop.ulaw2lin(mulaw_data, 1)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(linear_data)
            
        return wav_buffer.getvalue()
    except Exception as e:
        logger.error(f"Error converting μ-law to WAV: {e}")
        return b''

def save_audio_file(audio_data: bytes, filename: str, format: str = 'wav'):
    """Save audio data to file"""
    try:
        # Get the current directory and create recordings folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        recordings_dir = os.path.join(os.path.dirname(current_dir), 'recordings')
        os.makedirs(recordings_dir, exist_ok=True)
        
        filepath = os.path.join(recordings_dir, filename)
        
        if format == 'wav':
            with open(filepath, 'wb') as f:
                f.write(audio_data)
        elif format == 'ulaw':
            with open(filepath, 'wb') as f:
                f.write(audio_data)
                
        return filepath
    except Exception as e:
        logger.error(f"Error saving audio file: {e}")
        return None

def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    import re
    # Basic phone number validation (adjust regex as needed)
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone_number.replace(' ', '').replace('-', '')))

def format_transcript_for_display(transcript_entries: List[dict]) -> str:
    """Format transcript entries for readable display"""
    formatted = []
    for entry in transcript_entries:
        speaker = "किसान" if entry['speaker'] == 'farmer' else "कृषि सार्थी"
        timestamp = entry['timestamp'].strftime("%H:%M:%S") if hasattr(entry['timestamp'], 'strftime') else str(entry['timestamp'])
        formatted.append(f"[{timestamp}] {speaker}: {entry['message']}")
    
    return "\n".join(formatted)

def calculate_call_duration(start_time, end_time) -> int:
    """Calculate call duration in seconds"""
    try:
        if hasattr(start_time, 'timestamp') and hasattr(end_time, 'timestamp'):
            return int((end_time - start_time).total_seconds())
        return 0
    except Exception:
        return 0