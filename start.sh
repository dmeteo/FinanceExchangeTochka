#!/usr/bin/env bash
set -e

echo "⏳ Waiting for PostgreSQL..."
./wait_alembic.sh db

echo "🛠 Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload