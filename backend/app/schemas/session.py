from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    pass


class SessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None


class SessionMetadata(BaseModel):
    """Schema for agent metadata updates."""
    session_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    room_name: str
    created_at: datetime
    ended_at: Optional[datetime]


class SessionList(BaseModel):
    items: list[SessionRead]
