#!/bin/bash
# Runs both the backend (FastAPI, port 8001) and frontend (Vite, port 5173)
# together from a single terminal window/tab.
#
# Usage:
#   cd ai-health-report-analyzer
#   ./run.sh
#
# Press Ctrl+C once to stop BOTH servers.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=================================================="
echo " AI Health Report Analyzer — starting everything"
echo "=================================================="

# ---------- Backend setup ----------
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
  echo "[backend] Creating virtual environment (first run only)..."
  python3 -m venv venv
fi

echo "[backend] Activating venv & checking dependencies..."
source venv/bin/activate
python3 -m pip install -q -r requirements.txt

echo "[backend] Starting FastAPI on http://127.0.0.1:8001 ..."
uvicorn app.main:app --reload --port 8001 &
BACKEND_PID=$!

# Give the backend a moment to boot before starting the frontend
sleep 2

# ---------- Frontend setup ----------
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "[frontend] Installing npm packages (first run only)..."
  npm install
fi

echo "[frontend] Starting Vite on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!

# ---------- Cleanup on Ctrl+C ----------
cleanup() {
  echo ""
  echo "Stopping backend and frontend..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo "Stopped. Bye!"
  exit 0
}
trap cleanup INT TERM

echo ""
echo "=================================================="
echo " Backend:  http://127.0.0.1:8001"
echo " Frontend: http://localhost:5173   <-- open this in your browser"
echo " Press Ctrl+C to stop both."
echo "=================================================="

wait
