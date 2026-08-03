import logging
import uuid
from datetime import datetime
from typing import Any

from app.database import get_db
from app.models.session import Session
from app.schemas.session import (
    SessionCreate,
    SessionList,
    SessionMetadata,
    SessionRead,
    SessionUpdate,
)
from app.services.livekit import dispatch_stt_agent
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> Session:
    session_id = uuid.uuid4()
    session = Session(id=session_id, room_name=f"room-{session_id}")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    await dispatch_stt_agent(room_name=session.room_name)

    return session


@router.get("", response_model=SessionList)
async def list_sessions(db: AsyncSession = Depends(get_db)) -> SessionList:
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    return SessionList(items=list(result.scalars().all()))


async def _get_or_create_session_by_room_name(room_name: str, db: AsyncSession) -> Session:
    """Get a session by room name, or create it. Race-safe: if a concurrent
    request (e.g. two rapid agent callbacks) creates the row first, recover
    by re-selecting instead of crashing on the unique constraint violation."""
    result = await db.execute(select(Session).where(Session.room_name == room_name))
    session = result.scalars().first()
    if session is not None:
        return session

    session = Session(id=uuid.uuid4(), room_name=room_name)
    db.add(session)
    try:
        await db.commit()
        await db.refresh(session)
        return session
    except IntegrityError:
        logger.info("Lost race creating session for room %s, re-fetching", room_name)
        await db.rollback()
        result = await db.execute(select(Session).where(Session.room_name == room_name))
        session = result.scalars().first()
        if session is None:
            raise  # genuinely unexpected — re-raise so it surfaces properly
        return session


# Agent endpoint - update session metadata by room name (MUST come before /{session_id} routes)
@router.post("/room/{room_name}/metadata", response_model=SessionRead)
async def update_session_metadata_by_room_name(
    room_name: str,
    body: SessionMetadata,
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Update session metadata (start/end times, status) identified by room name."""
    logger.info("Received metadata update: room_name=%s, body=%s", room_name, body.model_dump())

    session = await _get_or_create_session_by_room_name(room_name, db)

    if body.end_time:
        try:
            session.ended_at = datetime.fromisoformat(body.end_time)
        except (ValueError, TypeError) as e:
            logger.error("Invalid end_time format for room %s: %s", room_name, e)
            raise HTTPException(status_code=400, detail=f"Invalid end_time: {e}")

    # start_time / status were previously accepted but silently dropped —
    # persist them too if your Session model has matching columns.
    if body.start_time and hasattr(session, "started_at"):
        try:
            session.started_at = datetime.fromisoformat(body.start_time)
        except (ValueError, TypeError) as e:
            logger.error("Invalid start_time format for room %s: %s", room_name, e)
            raise HTTPException(status_code=400, detail=f"Invalid start_time: {e}")

    if body.status and hasattr(session, "status"):
        session.status = body.status

    await db.commit()
    await db.refresh(session)
    logger.info("Successfully updated metadata for room %s", room_name)
    return session


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionRead)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if body.ended_at is not None:
        session.ended_at = body.ended_at

    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(session)
    await db.commit()