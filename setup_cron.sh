#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG="$PROJECT_DIR/data/cron.log"

CRON_JOB="0 8 * * * $PYTHON $PROJECT_DIR/main.py >> $LOG 2>&1"

# Add only if not already present
(crontab -l 2>/dev/null | grep -qF "$PROJECT_DIR/main.py") \
  && echo "Cron job already exists. No changes made." \
  || (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job scheduled:"
crontab -l | grep "main.py"
