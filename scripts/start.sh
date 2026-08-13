#!/usr/bin/env bash
# Build and run the app. Mac and Linux.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "No .env found in $ROOT. Create one with OPENROUTER_API_KEY and SESSION_SECRET."
  exit 1
fi

docker build -t pm-app .
docker rm -f pm-app >/dev/null 2>&1 || true
docker run -d \
  --name pm-app \
  -p 8000:8000 \
  --env-file .env \
  -v pm-data:/app/data \
  pm-app

echo "Running at http://localhost:8000"
