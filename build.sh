#!/usr/bin/env bash
set -euo pipefail

# Setup only — run as BUILD command on Railway/Render/Fly
# Usage: bash build.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Installing dependencies..."
$PYTHON -m pip install -r requirements.txt

echo "==> Running migrations..."
$PYTHON manage.py migrate --noinput

echo "==> Seeding demo data..."
$PYTHON manage.py seed_data

echo "==> Collecting static files..."
$PYTHON manage.py collectstatic --noinput

echo "==> Build complete."
