from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptCreate(BaseModel):
    text: str = Field(min_length=1)
    participant_identity: str = Field(min_length=1)
    start_time: datetime
    end_time: datetime


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    text: str
    participant_identity: str
    start_time: datetime
    end_time: datetime
    created_at: datetime


class TranscriptUpdate(BaseModel):
    text: str = Field(min_length=1)


class TranscriptList(BaseModel):
    items: list[TranscriptRead]


class TranscriptBulkCreate(BaseModel):
    """Payload for storing an entire session's transcript in one request,
    instead of one HTTP call per segment."""
    items: list[TranscriptCreate]


class TranscriptBulkRead(BaseModel):
    items: list[TranscriptRead]
    count: int