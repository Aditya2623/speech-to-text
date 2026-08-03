#!/bin/bash
set -e

# Start the LiveKit agent in the background
python agent/agent.py start &

# Start FastAPI in the foreground (keeps container alive)
uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}