#!/usr/bin/env bash
# =============================================================================
#  Aether Guide — 一键启动脚本 (macOS / Linux)
#
#  同时拉起 FastAPI (8000)、游客端 (3001)、管理端 (3002),等服务就绪后
#  自动在默认浏览器中打开游客端。Ctrl+C 会优雅清理所有子进程与端口。
#
#  用法:
#    ./start.sh                  # 默认:API + 游客端 + 管理端
#    ./start.sh --no-admin       # 跳过管理端
#    ./start.sh --no-tourist     # 跳过游客端
#    ./start.sh --no-open        # 不自动打开浏览器
#    ./start.sh --docker         # 额外启动 postgres/redis/minio
#    ./start.sh --clean          # 启动前清理 .next 缓存
#    ./start.sh --skip-install   # 跳过 npm install / uv sync
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

API_PORT=8000
TOURIST_PORT=3001
ADMIN_PORT=3002

NO_ADMIN=0
NO_TOURIST=0
NO_OPEN=0
DO_CLEAN=0
DO_DOCKER=0
SKIP_INSTALL=0

for arg in "$@"; do
  case "$arg" in
    --no-admin)     NO_ADMIN=1 ;;
    --no-tourist)   NO_TOURIST=1 ;;
    --no-open)      NO_OPEN=1 ;;
    --clean)        DO_CLEAN=1 ;;
    --docker)       DO_DOCKER=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    -h|--help)
      sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^#\s\?//'
      exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# ---------- helpers ----------------------------------------------------------
c_step() { printf '\033[1;36m==> %s\033[0m\n' "$*"; }
c_ok()   { printf '\033[0;32m  OK  %s\033[0m\n' "$*"; }
c_warn() { printf '\033[0;33m  !!  %s\033[0m\n' "$*"; }
c_err()  { printf '\033[0;31m  XX  %s\033[0m\n' "$*"; }

require() {
  command -v "$1" >/dev/null 2>&1 || { c_err "missing required tool: $1"; exit 1; }
}

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [[ -n "${pids:-}" ]]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
      c_warn "killed stale PIDs on :$port ($pids)"
    fi
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi
}

wait_http() {
  local url="$1" label="$2" timeout="${3:-90}"
  local elapsed=0
  while (( elapsed < timeout )); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      c_ok "$label ready ($url)"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  c_err "$label not ready within ${timeout}s ($url)"
  return 1
}

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then open "$url" >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 &
  else c_warn "no 'open' or 'xdg-open' found; visit $url manually"
  fi
}

# Track PIDs of child processes so the trap can clean them up.
PIDS=()
cleanup() {
  echo
  c_step "Shutting down all services"
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  # final belt-and-suspenders: free target ports
  for port in "$API_PORT" "$TOURIST_PORT" "$ADMIN_PORT"; do kill_port "$port"; done
  c_ok "stopped"
}
trap cleanup INT TERM EXIT

# ---------- preflight --------------------------------------------------------
c_step "Preflight checks"
require node
require npm
require uv
c_ok "uv / node / npm found"

# .env import — best effort; missing file is fine.
set -a
[[ -f "$ROOT/.env" ]]       && source "$ROOT/.env"       || true
[[ -f "$ROOT/.env.local" ]] && source "$ROOT/.env.local" || true
set +a
: "${AETHER_STORAGE_MODE:=inmemory}"
export AETHER_STORAGE_MODE
c_ok "AETHER_STORAGE_MODE=$AETHER_STORAGE_MODE"

export UV_CACHE_DIR="$ROOT/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$ROOT/.uv-python"

# ---------- optional docker --------------------------------------------------
if (( DO_DOCKER )); then
  require docker
  c_step "Starting infra containers (postgres / redis / minio)"
  docker compose -f infra/docker-compose.yml up -d postgres redis minio
  c_ok "infra up"
fi

if [[ "$AETHER_STORAGE_MODE" == "database" ]]; then
  c_step "Running Alembic migrations"
  (cd "$ROOT/apps/api" && uv run alembic upgrade head)
  c_ok "migrations applied"
fi

# ---------- dependencies -----------------------------------------------------
if (( ! SKIP_INSTALL )); then
  if [[ ! -d "$ROOT/node_modules" ]]; then
    c_step "Installing npm dependencies (first run may take minutes)..."
    npm install
    c_ok "npm install done"
  else
    c_ok "node_modules present (skip)"
  fi

  if [[ ! -d "$ROOT/.venv" ]]; then
    c_step "Creating Python virtualenv via uv sync..."
    uv sync --project apps/api
    c_ok "uv sync done"
  else
    c_ok ".venv present (skip)"
  fi
fi

# ---------- optional clean ---------------------------------------------------
if (( DO_CLEAN )); then
  for d in apps/web-tourist/.next apps/web-admin/.next; do
    [[ -d "$ROOT/$d" ]] && { rm -rf "$ROOT/$d"; c_warn "removed $d"; }
  done
fi

# ---------- clear stale port occupants ---------------------------------------
c_step "Freeing target ports"
TARGETS=("$API_PORT")
(( NO_TOURIST )) || TARGETS+=("$TOURIST_PORT")
(( NO_ADMIN   )) || TARGETS+=("$ADMIN_PORT")
for port in "${TARGETS[@]}"; do kill_port "$port"; done
c_ok "ports freed: ${TARGETS[*]}"

mkdir -p "$ROOT/.local"

# ---------- launch services --------------------------------------------------
# Each service is backgrounded and tagged with a colored prefix so the main
# terminal multiplexes their output readably. Logs are also tee'd to .local/.
spawn() {
  local label="$1" color="$2" logfile="$3"
  shift 3
  ("$@" 2>&1 | while IFS= read -r line; do
      printf '\033[%sm[%s]\033[0m %s\n' "$color" "$label" "$line"
      printf '%s\n' "$line" >> "$logfile"
   done) &
  PIDS+=("$!")
}

c_step "Launching services"

spawn 'API    ' '1;34' "$ROOT/.local/api.log" \
  uv run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port "$API_PORT"

if (( ! NO_TOURIST )); then
  spawn 'TOURIST' '1;32' "$ROOT/.local/web-tourist.log" \
    npm --workspace @aether/web-tourist run dev
fi

if (( ! NO_ADMIN )); then
  spawn 'ADMIN  ' '1;35' "$ROOT/.local/web-admin.log" \
    npm --workspace @aether/web-admin run dev
fi

# ---------- readiness + open browser -----------------------------------------
API_OK=1;    wait_http "http://localhost:$API_PORT/docs" 'API' 90 || API_OK=0
TOURIST_OK=1
if (( ! NO_TOURIST )); then
  wait_http "http://localhost:$TOURIST_PORT" 'Tourist' 120 || TOURIST_OK=0
fi
ADMIN_OK=1
if (( ! NO_ADMIN )); then
  wait_http "http://localhost:$ADMIN_PORT" 'Admin' 120 || ADMIN_OK=0
fi

if (( ! NO_OPEN )); then
  if (( ! NO_TOURIST )) && (( TOURIST_OK )); then
    open_url "http://localhost:$TOURIST_PORT"
  elif (( API_OK )); then
    open_url "http://localhost:$API_PORT/docs"
  fi
fi

echo
echo "=============================================================="
echo "  Aether Guide is running"
echo "=============================================================="
echo "  API        http://localhost:$API_PORT/docs"
(( NO_TOURIST )) || echo "  Tourist    http://localhost:$TOURIST_PORT"
(( NO_ADMIN   )) || echo "  Admin      http://localhost:$ADMIN_PORT"
echo
echo "  Press Ctrl+C to stop all services."
echo

# Park the main process until the user interrupts. `wait` is friendlier than a
# busy-loop and will return when any child exits or a signal arrives.
wait
