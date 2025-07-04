#!/bin/bash
set -e

echo "Waiting for Postgres..."
until pg_isready -h "pgvector-db" -p 5432 -U "$POSTGRES_USER"; do
  sleep 1
done

echo "Running init.sql via psql..."
PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h "pgvector-db" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f init.sql

echo "Starting app..."
exec python main.py
