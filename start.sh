#!/bin/bash
set -e

# Start the LiveKit agent in the background
cd agent/ && python agent.py start &

# Start FastAPI in the foreground, from the backend directory
cd backend/ && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}