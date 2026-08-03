import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    WorkerOptions,
    room_io,
)
from livekit.plugins import groq

load_dotenv(".env")
load_dotenv()

logger = logging.getLogger("stt-agent")
BACKEND_URL = os.environ["BACKEND_URL"].rstrip("/")
AGENT_NAME = os.environ.get("LIVEKIT_AGENT_NAME", "stt-agent")

TRANSCRIPTS_DIR = os.environ.get("TRANSCRIPTS_DIR", "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

logger.info("Agent configured with BACKEND_URL=%s", BACKEND_URL)
logger.info("Transcripts will be written to ./%s/<session_id>.txt", TRANSCRIPTS_DIR)

async def post_to_backend(path: str, payload: dict, *, what: str) -> None:
    """POST a JSON payload to the FastAPI backend. Used for both transcript
    storage and session metadata — same failure modes, same handling."""
    url = f"{BACKEND_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Stored %s (%s)", what, url)
    except httpx.HTTPStatusError as e:
        logger.error(
            "Failed to store %s: HTTP %s - %s (URL: %s)",
            what,
            e.response.status_code,
            e.response.text,
            url,
        )
    except Exception as e:
        # Always log type + repr so connection-level failures (refused,
        # DNS, timeout) are actually diagnosable instead of printing blank.
        logger.error(
            "Failed to store %s: %s: %r (URL: %s)",
            what,
            type(e).__name__,
            e,
            url,
        )


class TranscriptionAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")


def write_full_transcript(session_id: str, segments: list[str]) -> None:
    """Write the entire session's transcript as one combined file, in
    addition to the per-segment safety writes. Called once at session end."""
    path = os.path.join(TRANSCRIPTS_DIR, f"{session_id}.full.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(segments) + "\n")
        logger.info("Wrote full combined transcript to %s (%d segments)", path, len(segments))
    except Exception as e:
        logger.error("Failed to write full transcript to %s: %s: %r", path, type(e).__name__, e)


async def entrypoint(ctx: agents.JobContext) -> None:
    session_id = ctx.room.name
    pending_start: dict[str, datetime] = {}
    transcript_segments: list[str] = []
    transcript_bulk_items: list[dict] = []

    session = AgentSession(
        stt=groq.STT(
            model="whisper-large-v3-turbo",
            detect_language=True,
            api_key=os.getenv("GROQ_API_KEY"),
        ),
    )

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent) -> None:
        if ev.old_state == "initializing":
            start_time = datetime.now(timezone.utc)
            logger.info("Agent started at %s for session %s", start_time, session_id)
            asyncio.create_task(
                post_to_backend(
                    f"/sessions/room/{session_id}/metadata",
                    {
                        "session_id": session_id,
                        "start_time": start_time.isoformat(),
                        "status": "started",
                    },
                    what=f"session start metadata for {session_id}",
                )
            )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        identity = resolve_user_identity(ctx, ev)
        end_time = datetime.fromtimestamp(ev.created_at, tz=timezone.utc)

        if not ev.is_final:
            pending_start.setdefault(identity, end_time)
            return

        start_time = pending_start.pop(identity, end_time)

        transcript_segments.append(
            f"[{start_time.isoformat()} -> {end_time.isoformat()}] {identity}: {ev.transcript}"
        )
        transcript_bulk_items.append(
            {
                "text": ev.transcript,
                "participant_identity": identity,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
        )

    def on_participant_disconnected(participant) -> None:
        end_time = datetime.now(timezone.utc)
        logger.info(
            "Participant %s disconnected at %s for session %s",
            participant.identity,
            end_time,
            session_id,
        )

        if transcript_bulk_items:
            asyncio.create_task(
                post_to_backend(
                    f"/sessions/room/{session_id}/transcripts/bulk",
                    {"items": transcript_bulk_items},
                    what=f"bulk transcript ({len(transcript_bulk_items)} segments) for session {session_id}",
                )
            )

        asyncio.create_task(
            post_to_backend(
                f"/sessions/room/{session_id}/metadata",
                {
                    "session_id": session_id,
                    "end_time": end_time.isoformat(),
                    "status": "ended",
                },
                what=f"session end metadata for {session_id}",
            )
        )

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    await session.start(
        room=ctx.room,
        agent=TranscriptionAgent(),
        room_options=room_io.RoomOptions(
            text_output=room_io.TextOutputOptions(sync_transcription=False),
        ),
    )


def resolve_user_identity(ctx: agents.JobContext, ev: UserInputTranscribedEvent) -> str:
    return "user"


if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))