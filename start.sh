#!/usr/bin/env bash
set -e

echo "Waiting for PostgreSQL..."
./wait_alembic.sh db

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers $(nproc)
