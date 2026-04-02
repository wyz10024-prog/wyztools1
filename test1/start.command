#!/bin/zsh
set -e

ROOT="/Users/wyz/Documents/vscodeproject/test1"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

BACKEND_PORT=5051
FRONTEND_PORT=8081
LAN_IP=$(/usr/sbin/ipconfig getifaddr en0 2>/dev/null || /usr/sbin/ipconfig getifaddr en1 2>/dev/null || true)

echo "Starting backend..."
HOST=0.0.0.0 /usr/bin/python3 "$BACKEND_DIR/app.py" &
BACKEND_PID=$!

echo "Starting frontend..."
cd "$FRONTEND_DIR"
/usr/bin/python3 -m http.server "$FRONTEND_PORT" --bind 0.0.0.0 &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' INT TERM

sleep 1
open "http://127.0.0.1:${FRONTEND_PORT}"

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Local URL: http://127.0.0.1:${FRONTEND_PORT}"
if [ -n "$LAN_IP" ]; then
  echo "LAN URL: http://${LAN_IP}:${FRONTEND_PORT}"
  echo "LAN API: http://${LAN_IP}:${BACKEND_PORT}"
fi
echo "Press Ctrl+C to stop."
wait
