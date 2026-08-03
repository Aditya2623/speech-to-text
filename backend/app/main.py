from contextlib import asynccontextmanager

from app.config import settings
from app.routers import sessions, token, transcripts
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from backend.app.routers import transcripts


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Speech-to-Text API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(token.router)
app.include_router(sessions.router)
app.include_router(transcripts.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
