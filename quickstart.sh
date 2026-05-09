#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
VOICE_DIR="$ROOT_DIR/outbound-voice-agent"
ENV_FILE="$ROOT_DIR/.env"
VENV_DIR="$ROOT_DIR/.venv"
VOICE_PORT="${PORT:-5178}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.example" "$ENV_FILE"
  cat <<MSG
Created $ENV_FILE from .env.example.
Add your OpenAI API key to OPENAI_API_KEY, then run:

  ./quickstart.sh
MSG
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

VOICE_PORT="${PORT:-5178}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
OPENAI_API_KEY_VALUE="${OPENAI_API_KEY:-}"
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://hpao:hpao@localhost:5432/hpao}"
SAFETY_IDENTIFIER="${SAFETY_IDENTIFIER:-outbound-voice-agent-local}"
# VITE_API_URL is read by the React frontend at build/dev time; defaults
# to the backend port we just decided on. WS URL is auto-derived in
# frontend/src/api/realtime.ts (http -> ws), so it doesn't need to be set.
VITE_API_URL="${VITE_API_URL:-http://localhost:${BACKEND_PORT}}"
export DATABASE_URL PORT FRONTEND_PORT SAFETY_IDENTIFIER VITE_API_URL

if [[ -z "$OPENAI_API_KEY_VALUE" || "$OPENAI_API_KEY_VALUE" == "sk-your-api-key" ]]; then
  cat <<MSG
Set OPENAI_API_KEY in $ENV_FILE before starting the demo.

Example:
  OPENAI_API_KEY=sk-your-api-key
MSG
  exit 1
fi

open_url() {
  local url="$1"

  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
  else
    printf 'Open: %s\n' "$url"
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"

  for _ in {1..60}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      printf '%s ready at %s\n' "$label" "$url"
      return 0
    fi
    sleep 1
  done

  printf '%s did not become ready at %s\n' "$label" "$url" >&2
  return 1
}

npm_install_app() {
  local app_dir="$1"
  local label="$2"

  if [[ -f "$app_dir/package-lock.json" ]]; then
    if npm --prefix "$app_dir" ci; then
      return 0
    fi
  else
    if npm --prefix "$app_dir" install; then
      return 0
    fi
  fi

  printf '%s dependency install failed. Removing node_modules and retrying once...\n' "$label" >&2
  rm -rf "$app_dir/node_modules"

  if [[ -f "$app_dir/package-lock.json" ]]; then
    npm --prefix "$app_dir" ci
  else
    npm --prefix "$app_dir" install
  fi
}

cleanup() {
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    printf '\nStopping demo servers...\n'
    kill "${PIDS[@]}" >/dev/null 2>&1 || true
  fi
}

PIDS=()
trap cleanup EXIT INT TERM

printf 'Preparing ABE core/data logic...\n'
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install -e "$ROOT_DIR[dev]" >/dev/null

BACKEND_AVAILABLE=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  # cd into ROOT_DIR so docker compose auto-loads docker-compose.override.yml
  # if the dev has one (gitignored, used to dodge host-port collisions).
  # `--wait` blocks until the db's healthcheck passes so alembic doesn't
  # race the still-initializing Postgres process on a cold first run.
  (cd "$ROOT_DIR" && docker compose up -d --wait db)
  (cd "$ROOT_DIR" && "$VENV_DIR/bin/alembic" -c "$ROOT_DIR/alembic.ini" upgrade head)
  printf 'Seeding demo school + classes + students (idempotent)...\n'
  (cd "$ROOT_DIR" && "$VENV_DIR/bin/python" -m hpao.cli.seed)
  printf 'Seeding Avery Johnson + 14 hall-pass history (idempotent)...\n'
  (cd "$ROOT_DIR" && "$VENV_DIR/bin/python" -m hpao.cli.seed_avery)
  BACKEND_AVAILABLE=1
else
  printf 'Docker is not running; skipping local Postgres + ABE backend startup. The Teacher Dashboard / Hall Pass iPad will fail their first /api/sessions fetch until you start Docker and re-run.\n'
fi

printf 'Installing Teacher Dashboard / Hall Pass iPad dependencies...\n'
npm_install_app "$FRONTEND_DIR" "Teacher Dashboard / Hall Pass iPad"

printf 'Installing Outbound Voice Agent dependencies...\n'
npm_install_app "$VOICE_DIR" "Outbound Voice Agent"

if [[ $BACKEND_AVAILABLE -eq 1 ]]; then
  printf 'Starting ABE backend (uvicorn) on port %s...\n' "$BACKEND_PORT"
  (cd "$ROOT_DIR" && "$VENV_DIR/bin/uvicorn" --factory hpao.app:app_factory \
    --host 127.0.0.1 --port "$BACKEND_PORT") &
  PIDS+=("$!")
fi

printf 'Starting Teacher Dashboard and Hall Pass iPad app...\n'
npm --prefix "$FRONTEND_DIR" run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" &
PIDS+=("$!")

printf 'Starting Outbound Voice Agent...\n'
npm --prefix "$VOICE_DIR" start &
PIDS+=("$!")

TEACHER_DASHBOARD_URL="http://localhost:${FRONTEND_PORT}/classes"
IPAD_APP_URL="http://localhost:${FRONTEND_PORT}/classes"
OUTBOUND_VOICE_AGENT_URL="http://localhost:${VOICE_PORT}"
BACKEND_HEALTHZ_URL="http://localhost:${BACKEND_PORT}/healthz"

if [[ $BACKEND_AVAILABLE -eq 1 ]]; then
  wait_for_url "$BACKEND_HEALTHZ_URL" "ABE backend"
fi
wait_for_url "http://localhost:${FRONTEND_PORT}" "Teacher Dashboard / Hall Pass iPad"
wait_for_url "$OUTBOUND_VOICE_AGENT_URL" "Outbound Voice Agent"

printf '\nOpening demo URLs...\n'
printf 'Teacher Dashboard: %s\n' "$TEACHER_DASHBOARD_URL"
printf 'Hall Pass iPad:    %s\n' "$IPAD_APP_URL"
printf 'Voice Agent:       %s\n' "$OUTBOUND_VOICE_AGENT_URL"

open_url "$TEACHER_DASHBOARD_URL"
open_url "$IPAD_APP_URL"
open_url "$OUTBOUND_VOICE_AGENT_URL"

printf '\nAll demo components are running. Press Ctrl+C to stop the local servers.\n'
wait
