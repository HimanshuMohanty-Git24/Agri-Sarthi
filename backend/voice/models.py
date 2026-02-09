"""
Pydantic models for voice call module.
"""
from pydantic import BaseModel
from typing import Optional


class VoiceCallCreate(BaseModel):
    """Request to create an outbound call."""
    to: str                               # E.164 phone number, e.g. "+919876543210"
    webhook_url: Optional[str] = None
    from_number: Optional[str] = None     # Override Twilio FROM number


class CallRecord(BaseModel):
    """Stored call record."""
    call_sid: str
    direction: str                        # "inbound" or "outbound"
    from_number: str
    to_number: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "in-progress"


class TranscriptEntry(BaseModel):
    """Single line in a call transcript."""
    role: str                             # "farmer" or "agent"
    text: str
    language: Optional[str] = None
