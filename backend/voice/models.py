from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class CallStatus(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Speaker(str, Enum):
    FARMER = "farmer"
    AI = "ai"

class VoiceCallCreate(BaseModel):
    phone_number: str
    farmer_name: Optional[str] = None
    
class VoiceCallResponse(BaseModel):
    id: str
    phone_number: str
    call_sid: str
    status: CallStatus
    duration: Optional[int] = None
    farmer_name: Optional[str] = None
    conversation_summary: Optional[str] = None
    created_at: datetime
    
class TranscriptEntry(BaseModel):
    speaker: Speaker
    message: str
    language: str = "hi-IN"
    timestamp: datetime
    
class CallTranscript(BaseModel):
    call_id: str
    entries: List[TranscriptEntry]
    
class AudioChunk(BaseModel):
    event: str
    streamSid: Optional[str] = None
    media: Optional[Dict] = None
    start: Optional[Dict] = None

class FarmerVoicePreference(BaseModel):
    farmer_id: Optional[str] = None
    preferred_language: str = "hi-IN"
    voice_calls_enabled: bool = True
    
class VoiceCallUpdate(BaseModel):
    status: Optional[CallStatus] = None
    duration: Optional[int] = None
    conversation_summary: Optional[str] = None