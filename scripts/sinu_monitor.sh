#!/bin/bash
# SINU monitor cron wrapper.
# Usage: sinu_monitor.sh [check|enroll|watch]
# Designed to run from cron; prints JSON to stdout.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

MODE="${1:-check}"
PYTHON="${PYTHON:-python3}"

exec "$PYTHON" -m sinu_auto "$MODE" --config config/settings.yaml --env .env
