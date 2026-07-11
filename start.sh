#!/usr/bin/env bash
set -euo pipefail

# Full local startup (setup + run). For production PaaS, use build.sh + gunicorn separately.
# Usage:
#   bash start.sh          # production (gunicorn)
#   bash start.sh dev      # local dev server
#   PORT=8080 bash start.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="${1:-prod}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "==> Sayed Microbus startup ($MODE)"

# Local dev: create venv if missing. Production PaaS skips this — uses system Python.
if [[ ! -f .venv/bin/activate ]] && [[ "$MODE" == "dev" ]]; then
  echo "==> Creating virtual environment..."
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
fi

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"

echo "==> Installing dependencies..."
$PYTHON -m pip install -r requirements.txt

echo "==> Running migrations..."
$PYTHON manage.py migrate --noinput

echo "==> Seeding demo data..."
$PYTHON manage.py seed_data

echo "==> Collecting static files..."
$PYTHON manage.py collectstatic --noinput

if [[ "$MODE" == "dev" ]]; then
  echo "==> Starting development server on http://127.0.0.1:${PORT}"
  exec $PYTHON manage.py runserver "${HOST}:${PORT}"
fi

echo "==> Starting gunicorn on http://${HOST}:${PORT}"
exec gunicorn buildathon.wsgi:application --bind "${HOST}:${PORT}"
