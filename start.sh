#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$RUN_DIR/sentiment-barometer.pid"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8787}"
PYTHON="${PYTHON:-python3}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "Service already running: pid=$PID url=http://$HOST:$PORT"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$ROOT_DIR"
nohup "$PYTHON" -m app.server --host "$HOST" --port "$PORT" > "$LOG_DIR/server.log" 2>&1 &
PID="$!"
echo "$PID" > "$PID_FILE"
disown "$PID" 2>/dev/null || true

for _ in {1..30}; do
  if curl -fsS "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
    echo "Service started: pid=$PID url=http://$HOST:$PORT"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Service failed to start. See $LOG_DIR/server.log"
    rm -f "$PID_FILE"
    exit 1
  fi
  sleep 0.2
done

if kill -0 "$PID" 2>/dev/null; then
  echo "Service process started but health check timed out: pid=$PID url=http://$HOST:$PORT"
  echo "See $LOG_DIR/server.log"
  exit 1
else
  echo "Service failed to start. See $LOG_DIR/server.log"
  rm -f "$PID_FILE"
  exit 1
fi
