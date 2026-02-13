#!/bin/bash

set -e

if [ -f .env.local ]; then
  export $(grep -v '^#' .env.local | xargs)
else
  echo ".env.local not found"
  exit 1
fi

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL not set"
  exit 1
fi

echo "Using DATABASE_URL=$DATABASE_URL"
gunicorn app:app
