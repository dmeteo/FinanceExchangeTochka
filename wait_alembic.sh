#!/usr/bin/env bash
set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -p 5432; do
  echo "Waiting for PostgreSQL at $host..."
  sleep 1
done

exec $cmd