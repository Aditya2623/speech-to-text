import logging
import uuid

from app.database import get_db
from app.models.session import Session
from app.models.transcript import Transcript
from app.schemas.transcript import (
    TranscriptBulkCreate,
    TranscriptBulkRead,
    TranscriptCreate,
    TranscriptList,
    TranscriptRead,
    TranscriptUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transcripts"])


async def _get_session_or_404(session_id: uuid.UUID, db: AsyncSession) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _get_session_by_room_name_or_create(room_name: str, db: AsyncSession) -> Session:
    """Get session by room name, or create if it doesn't exist. Race-safe:
    if a concurrent request (e.g. rapid-fire agent transcript callbacks for
    the same room) creates the row first, recover instead of crashing on
    the unique constraint violation."""
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


@router.get("/sessions/{session_id}/transcripts", response_model=TranscriptList)
async def list_session_transcripts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TranscriptList:
    await _get_session_or_404(session_id, db)
    result = await db.execute(
        select(Transcript)
        .where(Transcript.session_id == session_id)
        .order_by(Transcript.start_time.asc())
    )
    return TranscriptList(items=list(result.scalars().all()))


@router.post(
    "/sessions/{session_id}/transcripts",
    response_model=TranscriptRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_transcript(
    session_id: uuid.UUID,
    body: TranscriptCreate,
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    await _get_session_or_404(session_id, db)
    transcript = Transcript(
        session_id=session_id,
        text=body.text,
        participant_identity=body.participant_identity,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return transcript


@router.patch("/transcripts/{transcript_id}", response_model=TranscriptRead)
async def update_transcript(
    transcript_id: uuid.UUID,
    body: TranscriptUpdate,
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    transcript = await db.get(Transcript, transcript_id)
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    transcript.text = body.text
    await db.commit()
    await db.refresh(transcript)
    return transcript


@router.delete("/transcripts/{transcript_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcript(transcript_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    transcript = await db.get(Transcript, transcript_id)
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    await db.delete(transcript)
    await db.commit()


# Agent endpoint - accepts room_name instead of a session_id UUID.
#
# IMPORTANT FIX: this used to be registered as "/sessions/{room_name}/transcripts",
# which has the *identical path shape* as "/sessions/{session_id}/transcripts"
# above. FastAPI/Starlette match routes by path pattern, not parameter name —
# so only the first-registered route (the UUID one) ever matched, and this
# route was silently unreachable. Any request with a non-UUID room name
# (e.g. "console", or "room-<uuid>") would 422 against the UUID route instead
# of ever reaching this handler. Giving it a distinct prefix fixes that.
#
# NOTE: update your agent's BACKEND_URL path to match:
#   f"/sessions/room/{session_id}/transcripts"
@router.post(
    "/sessions/room/{room_name}/transcripts",
    response_model=TranscriptRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_transcript_by_room_name(
    room_name: str,
    body: TranscriptCreate,
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    """Create transcript for a session identified by room name."""
    session = await _get_session_by_room_name_or_create(room_name, db)

    transcript = Transcript(
        session_id=session.id,
        text=body.text,
        participant_identity=body.participant_identity,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return transcript


@router.post(
    "/sessions/room/{room_name}/transcripts/bulk",
    response_model=TranscriptBulkRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_transcripts_bulk(
    room_name: str,
    body: TranscriptBulkCreate,
    db: AsyncSession = Depends(get_db),
) -> TranscriptBulkRead:
    """Store an entire session's transcript in ONE request / ONE transaction.
    Preferred over calling create_transcript_by_room_name once per segment —
    avoids per-request DB round trips and the concurrency issues that come
    with many rapid-fire individual inserts for the same session."""
    session = await _get_session_by_room_name_or_create(room_name, db)

    if not body.items:
        return TranscriptBulkRead(items=[], count=0)

    transcripts = [
        Transcript(
            session_id=session.id,
            text=item.text,
            participant_identity=item.participant_identity,
            start_time=item.start_time,
            end_time=item.end_time,
        )
        for item in body.items
    ]
    db.add_all(transcripts)
    await db.commit()
    for t in transcripts:
        await db.refresh(t)

    logger.info("Bulk-stored %d transcript segments for room %s", len(transcripts), room_name)
    return TranscriptBulkRead(items=transcripts, count=len(transcripts))