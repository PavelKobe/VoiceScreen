#!/usr/bin/env bash
# Pull from GitHub, bring up containers, wait for Postgres, apply migrations.
# Intended to be run on the VM from ~/VoiceScreen.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> git pull"
git pull --ff-only

echo "==> activate venv"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> docker compose up -d postgres redis"
docker compose up -d postgres redis

echo "==> wait for Postgres"
for i in {1..30}; do
    if docker exec voicescreen-postgres-1 pg_isready -U voicescreen >/dev/null 2>&1; then
        echo "    Postgres ready"
        break
    fi
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo "    Postgres did not become ready in 30s" >&2
        exit 1
    fi
done

echo "==> alembic upgrade head"
alembic upgrade head

echo "==> done"
