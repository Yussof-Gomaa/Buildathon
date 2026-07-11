#!/usr/bin/env bash
set -euo pipefail

# Sayed Microbus — one-command startup (setup + run)
# Usage:
#   ./start.sh          # production (gunicorn, port 8000)
#   ./start.sh dev      # local dev server
#   PORT=8080 ./start.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="${1:-prod}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "==> Sayed Microbus startup ($MODE)"

if [[ ! -d .venv ]]; then
  echo "==> Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install -q -r requirements.txt

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Seeding demo data..."
python manage.py seed_data

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

if [[ "$MODE" == "dev" ]]; then
  echo "==> Starting development server on http://127.0.0.1:${PORT}"
  exec python manage.py runserver "${HOST}:${PORT}"
fi

echo "==> Starting gunicorn on http://${HOST}:${PORT}"
exec gunicorn buildathon.wsgi:application --bind "${HOST}:${PORT}"
