#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh  —  Starts the FastAPI backend + React frontend
# Usage:  bash start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    FinAI — Financial Research AI      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"

# 1. Copy Python modules into backend dir (so FastAPI can import them)
echo -e "\n${YELLOW}[1/4] Linking Python modules…${NC}"
for f in database.py fundamentals.py agent.py tools.py logger.py; do
  if [ -f "$ROOT/../$f" ]; then
    cp "$ROOT/../$f" "$BACKEND/$f"
    echo "  ✓ $f"
  elif [ -f "$ROOT/$f" ]; then
    cp "$ROOT/$f" "$BACKEND/$f"
    echo "  ✓ $f (from project root)"
  else
    echo "  ⚠  $f not found — place it next to start.sh or in backend/"
  fi
done

# Copy .env
if [ -f "$ROOT/../.env" ]; then
  cp "$ROOT/../.env" "$BACKEND/.env"
  echo "  ✓ .env"
elif [ -f "$ROOT/.env" ]; then
  cp "$ROOT/.env" "$BACKEND/.env"
  echo "  ✓ .env (from project root)"
else
  echo "  ⚠  .env not found — create one with GOOGLE_API_KEY=..."
fi

# 2. Python deps
echo -e "\n${YELLOW}[2/4] Installing Python dependencies…${NC}"
pip install -r "$BACKEND/requirements.txt" -q
echo "  ✓ Python packages installed"

# 3. Node deps
echo -e "\n${YELLOW}[3/4] Installing Node dependencies…${NC}"
cd "$FRONTEND"
npm install --legacy-peer-deps --silent
echo "  ✓ Node packages installed"

# 4. Launch both servers
echo -e "\n${YELLOW}[4/4] Starting servers…${NC}"
echo -e "  ${GREEN}Backend:${NC}  http://localhost:8000"
echo -e "  ${GREEN}Frontend:${NC} http://localhost:3000"
echo -e "  ${GREEN}API Docs:${NC} http://localhost:8000/docs\n"

# Kill any orphan processes on exit
trap 'kill $(jobs -p) 2>/dev/null; exit' INT TERM EXIT

# Start FastAPI
cd "$BACKEND"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to be ready
sleep 2

# Start React
cd "$FRONTEND"
BROWSER=none npm start &
FRONTEND_PID=$!

echo -e "${GREEN}✓ Both servers running. Press Ctrl+C to stop.${NC}\n"
wait
