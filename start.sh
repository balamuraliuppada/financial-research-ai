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

# 1. Ensure Python modules are available to the backend
echo -e "\n${YELLOW}[1/4] Linking Python modules…${NC}"
for f in database.py fundamentals.py agent.py tools.py logger.py; do
  if [ -f "$BACKEND/$f" ]; then
    echo "  ✓ $f"
  elif [ -f "$ROOT/$f" ]; then
    cp "$ROOT/$f" "$BACKEND/$f"
    echo "  ✓ $f (from project root)"
  elif [ -f "$ROOT/../$f" ]; then
    cp "$ROOT/../$f" "$BACKEND/$f"
    echo "  ✓ $f (from parent directory)"
  else
    echo "  ⚠  $f not found — place it next to start.sh or in backend/"
  fi
done

# Copy .env
if [ -f "$BACKEND/.env" ]; then
  echo "  ✓ .env"
elif [ -f "$ROOT/.env" ]; then
  cp "$ROOT/.env" "$BACKEND/.env"
  echo "  ✓ .env (from project root)"
elif [ -f "$ROOT/../.env" ]; then
  cp "$ROOT/../.env" "$BACKEND/.env"
  echo "  ✓ .env (from parent directory)"
else
  echo "  ⚠  .env not found — create one with GOOGLE_API_KEY=..."
fi

# 2. Python deps
echo -e "\n${YELLOW}[2/4] Installing Python dependencies…${NC}"
to_windows_path() {
  if command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$1"
  elif command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

resolve_python() {
  local candidate resolved
  for candidate in python.exe py.exe python3.exe python py python3; do
    if resolved=$(command -v "$candidate" 2>/dev/null); then
      case "$resolved" in
        *WindowsApps*) continue ;;
      esac
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

PYTHON_EXE="$(resolve_python)"
if [ -z "$PYTHON_EXE" ]; then
  echo "  ✗ Could not find a usable Python installation on PATH"
  exit 1
fi

if command -v wslpath >/dev/null 2>&1 && command -v cmd.exe >/dev/null 2>&1; then
  PYTHON_CMD=(cmd.exe /c py -3)
else
  PYTHON_CMD=("$PYTHON_EXE")
  case "$(basename "$PYTHON_EXE")" in
    py|py.exe)
      PYTHON_CMD=("$PYTHON_EXE" -3)
      ;;
  esac
fi

BACKEND_REQUIREMENTS="$BACKEND/requirements.txt"
if command -v wslpath >/dev/null 2>&1; then
  BACKEND_REQUIREMENTS_WIN="$(to_windows_path "$BACKEND_REQUIREMENTS")"
else
  BACKEND_REQUIREMENTS_WIN="$BACKEND_REQUIREMENTS"
fi

if ! "${PYTHON_CMD[@]}" -m pip --version >/dev/null 2>&1; then
  echo "  ⚠  pip is missing for ${PYTHON_CMD[*]}; attempting bootstrap…"
  "${PYTHON_CMD[@]}" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi

if ! "${PYTHON_CMD[@]}" -m pip --version >/dev/null 2>&1; then
  echo "  ✗ pip is still unavailable for ${PYTHON_CMD[*]}. Install pip in that Python environment and rerun."
  exit 1
fi

"${PYTHON_CMD[@]}" -m pip install -r "$BACKEND_REQUIREMENTS_WIN" -q
echo "  ✓ Python packages installed"

is_port_in_use() {
  "${PYTHON_CMD[@]}" -c "import socket,sys; s=socket.socket(); s.settimeout(0.2); r=s.connect_ex(('127.0.0.1', int(sys.argv[1]))); s.close(); sys.exit(0 if r == 0 else 1)" "$1"
}

FRONTEND_PORT=3000
while is_port_in_use "$FRONTEND_PORT"; do
  FRONTEND_PORT=$((FRONTEND_PORT + 1))
done

# 3. Node deps
echo -e "\n${YELLOW}[3/4] Installing Node dependencies…${NC}"
cd "$FRONTEND"
npm install --legacy-peer-deps --silent
echo "  ✓ Node packages installed"

# 4. Launch both servers
echo -e "\n${YELLOW}[4/4] Starting servers…${NC}"
echo -e "  ${GREEN}Backend:${NC}  http://localhost:8000"
echo -e "  ${GREEN}Frontend:${NC} http://localhost:${FRONTEND_PORT}"
echo -e "  ${GREEN}API Docs:${NC} http://localhost:8000/docs\n"

# Kill any orphan processes on exit
trap 'kill $(jobs -p) 2>/dev/null; exit' INT TERM EXIT

# Start FastAPI
cd "$BACKEND"
"${PYTHON_CMD[@]}" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to be ready
sleep 2

# Start React
cd "$FRONTEND"
PORT="$FRONTEND_PORT" BROWSER=none npm start &
FRONTEND_PID=$!

echo -e "${GREEN}✓ Both servers running. Press Ctrl+C to stop.${NC}\n"
wait
