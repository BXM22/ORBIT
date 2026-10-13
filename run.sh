#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

MAX_AGE=1800   # seconds: warn if the newest reading is older than 30 min

RUN_LINE="*/10 * * * * $DIR/run.sh >> $DIR/pipeline.log 2>&1"
CHECK_LINE="*/30 * * * * $DIR/run.sh check >> $DIR/check.log 2>&1"

run_pipeline() {
  docker compose up -d
  until docker compose exec -T db pg_isready -U postgres -d iss > /dev/null 2>&1; do
    sleep 1
  done
  .venv/bin/python pipeline.py
}

check_freshness() {
  local age
  age=$(docker compose exec -T db psql -U postgres -d iss -tA -c \
    "SELECT COALESCE(EXTRACT(EPOCH FROM (now() - max(observed_at)))::int, 999999) FROM raw_iss_positions;" \
    2>/dev/null) || age=999999
  age=${age:-999999}

  if [ "$age" -gt "$MAX_AGE" ]; then
    echo "$(date '+%F %T') STALE: newest reading is ${age}s old (limit ${MAX_AGE}s)"
    osascript -e 'display notification "ISS pipeline looks stalled. Check pipeline.log" with title "iss-pipeline"' 2>/dev/null || true
    exit 1
  fi
  echo "$(date '+%F %T') OK: newest reading is ${age}s old"
}

case "${1:-run}" in
  run)
    run_pipeline
    ;;
  check)
    check_freshness
    ;;
  install)
    { crontab -l 2>/dev/null | grep -vF "$DIR/run.sh" || true; echo "$RUN_LINE"; echo "$CHECK_LINE"; } | crontab -
    echo "Scheduled:"; echo "  $RUN_LINE"; echo "  $CHECK_LINE"
    ;;
  uninstall)
    { crontab -l 2>/dev/null | grep -vF "$DIR/run.sh" || true; } | crontab -
    echo "Removed the schedule"
    ;;
  status)
    crontab -l 2>/dev/null | grep -F "$DIR/run.sh" || echo "Not scheduled"
    ;;
  *)
    echo "Usage: ./run.sh [run|check|install|uninstall|status]"
    exit 1
    ;;
esac