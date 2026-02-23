#!/usr/bin/env bash
set -euo pipefail

echo "Killing existing celery workers..."
pkill -f 'celery.*app\.celery_app.*worker' 2>/dev/null && echo "Old workers killed." || echo "No existing workers found."

# Give processes time to exit
sleep 1

echo "Starting celery worker..."
cd "$(dirname "$0")/autograder-back"
exec uv run celery -A app.celery_app worker --loglevel=info
