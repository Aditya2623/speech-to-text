# Speech to Text

Personal speech-to-text app built on LiveKit rooms + a Python STT agent, with a FastAPI backend and Next.js frontend.

Live demo: https://speech-to-text-misd6d2pm-adityavardhan2623-1393s-projects.vercel.app/

> **Known issue:** The backend and STT agent run combined in a single container on Render's free tier (512MB RAM) to stay within a no-cost deployment. Under load, this can occasionally exceed the memory limit and cause the instance to restart ("Ran out of memory (used over 512MB)"). If the live demo seems unresponsive, it may be mid-restart — retrying after ~30–60 seconds usually resolves it. See [Troubleshooting](#troubleshooting) for details and possible fixes.

## Architecture

1. Frontend calls FastAPI to create a session and mint a LiveKit token.
2. Frontend connects directly to LiveKit Cloud over WebRTC and publishes mic audio.
3. A Python STT agent joins the same room, runs Groq STT, publishes live captions on the `transcription` text stream, and POSTs final segments to FastAPI.
4. FastAPI persists final transcript segments in Neon PostgreSQL.

```
Next.js (Vercel) ──HTTP──► FastAPI ──► Neon Postgres
      │                           │
      └──── WebRTC / text streams ┴──── LiveKit Cloud ◄── STT Agent
```

Locally, the FastAPI backend and the STT agent run as two separate processes
for easier development.

## Prerequisites

Create accounts and generate these values manually:

| Secret | Where to get it |
|--------|-----------------|
| `DATABASE_URL` | [Neon](https://neon.tech) → project → connection string (use async form below) |
| `LIVEKIT_URL` | [LiveKit Cloud](https://cloud.livekit.io) → Project Settings |
| `LIVEKIT_API_KEY` | LiveKit Cloud → Settings → Keys |
| `LIVEKIT_API_SECRET` | LiveKit Cloud → Settings → Keys |
| `GROQ_API_KEY` | [Groq](https://www.groq.com/) → API Keys |

Also install:

- Python 3.12+
- Node.js 20+
- [LiveKit CLI](https://docs.livekit.io/home/cli/cli-setup/) (`brew install livekit-cli`) — optional, useful for `lk agent logs` style debugging against LiveKit Cloud

## Local development

Locally, backend and agent run as two separate processes (simpler to debug than the combined production container).

### 1. Database (Neon)

Create a Neon project and copy the connection string. Convert it to SQLAlchemy async format:

```bash
# Postgres URL from Neon:
postgresql://user:pass@host/db?sslmode=require

# Use this in backend/.env:
DATABASE_URL=postgresql+asyncpg://user:pass@host/db?sslmode=require
```

Run migrations locally:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

### 2. Backend

```bash
cd backend
cp .env.example .env
```

Set at minimum:

```env
DATABASE_URL=postgresql+asyncpg://...
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
CORS_ORIGINS=http://localhost:3000
LIVEKIT_AGENT_NAME=stt-agent
```

Start:

```bash
uvicorn app.main:app --reload --port 8080
```

API docs: http://localhost:8080/docs

### 3. STT agent

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
GROQ_API_KEY=...
BACKEND_URL=http://localhost:8080
```

Run locally:

```bash
python agent.py dev
```

When you create a session from the frontend, the backend dispatches the `stt-agent` worker into the room automatically.

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

Set:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8080
```

Start:

```bash
npm run dev
```

Open http://localhost:3000, click **Start new session**, allow mic access, and speak.

## API summary

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/token` | Mint LiveKit JWT |
| POST | `/sessions` | Create session (`room-{uuid}`) + dispatch agent |
| GET | `/sessions` | List sessions |
| GET | `/sessions/{id}` | Get session |
| PATCH | `/sessions/{id}` | Update session (`ended_at`) |
| DELETE | `/sessions/{id}` | Delete session |
| GET | `/sessions/{id}/transcripts` | List saved segments |
| POST | `/sessions/{id}/transcripts` | Persist final segment (agent) |
| DELETE | `/transcripts/{id}` | Delete segment |

## STT provider

Default: **Groq whisper-large-v3-turbo** via `livekit-plugins-groq`. Fully
API-based — no model weights are downloaded or run locally, which keeps the
agent process lightweight enough to share a container with the backend on a
memory-limited free tier.

Alternatives supported by LiveKit Agents include Deepgram, AssemblyAI, and
local Silero. Groq is the default here because it matches the agent's
current configuration and uses the same LiveKit Groq plugin for STT.

## Project layout

```text
speech-to-text/
├── Dockerfile   Combined backend + agent image (Render deploy)
├── start.sh     Entrypoint: runs agent in background, uvicorn in foreground
├── backend/     FastAPI + SQLAlchemy + Alembic
├── agent/       livekit-agents STT worker
├── frontend/    Next.js + LiveKit React components
└── README.md
```

## Troubleshooting

- **No captions**: confirm the agent process is running (check Render logs
  for the `livekit.agents` worker registering — you should see something
  like `"worker is below capacity, marking as available"`) and that
  `LIVEKIT_AGENT_NAME` matches `stt-agent` on both backend and agent.
- **No saved history**: only final STT segments are persisted; interim
  captions are live-only.
- **404 on `//sessions` (double slash) in Render logs**: `NEXT_PUBLIC_BACKEND_URL`
  on Vercel has a trailing slash. Set it without one
  (`https://your-backend.onrender.com`, not `.../`), then trigger a fresh
  Vercel deploy — env var edits alone don't apply to an already-built
  deployment. The `request()` helper in `frontend/lib/api.ts` also strips any
  trailing slash defensively, so this shouldn't recur even if the env var is
  set with one.
- **Instance killed / "Ran out of memory (used over 512MB)"**: see the
  memory note under [Render deploy](#render-backend--agent-combined-service)
  above. Rule out local model loading first; if none is present, the overhead
  is likely just two Python processes in one small container.
- **DB connection errors**: ensure the Neon URL uses the
  `postgresql+asyncpg://` driver prefix, and that `sslmode=require` in the
  raw Neon string becomes `ssl=require` in the SQLAlchemy async DSN.