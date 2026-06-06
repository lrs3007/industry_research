#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.run/sentiment-barometer.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Service is not running: missing PID file"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ -z "$PID" ]] || ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Service is not running: stale PID file removed"
  exit 0
fi

kill "$PID"
for _ in {1..20}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Service stopped: pid=$PID"
    exit 0
  fi
  sleep 0.2
done

kill -TERM "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Service stop requested: pid=$PID"

