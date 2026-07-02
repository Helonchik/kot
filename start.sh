#!/bin/bash

# Start FastAPI dashboard in the background
echo "Starting FastAPI dashboard on port ${PORT:-8000}..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Save the PID of the background process
UVICORN_PID=$!

# Function to handle shutdown signals
cleanup() {
    echo "Shutting down..."
    kill -TERM "$UVICORN_PID" 2>/dev/null
    exit 0
}

# Trap SIGINT and SIGTERM to clean up background process
trap cleanup SIGINT SIGTERM

# Start Discord bot in the foreground
echo "Starting Discord bot..."
python -m app.bot.bot
