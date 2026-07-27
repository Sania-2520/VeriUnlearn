#!/usr/bin/env bash
# ==============================================================================
# VeriUnlearn — Deployment Validation Script
# ==============================================================================
# Checks Docker, Docker Compose, port availability, .env variables, and
# connectivity to all dependent services. Exits 0 only if all checks pass.
#
# Usage:
#   ./scripts/validate_deployment.sh              # quick validation
#   ./scripts/validate_deployment.sh --verbose    # detailed output
#   ./scripts/validate_deployment.sh --ci         # CI mode (exit on first fail)
# ==============================================================================
set -uo pipefail

# ─── Color / formatting ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ─── Config ─────────────────────────────────────────────────────────────────
VERBOSE=false
CI_MODE=false
FAIL_COUNT=0
WARN_COUNT=0
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

# Required services and their ports
declare -A REQUIRED_PORTS=(
  ["Backend API"]="8000"
  ["ML Engine"]="8001"
  ["Frontend"]="3000"
  ["PostgreSQL"]="5432"
  ["Redis"]="6379"
  ["Qdrant"]="6333"
  ["MinIO API"]="9000"
  ["MinIO Console"]="9001"
  ["HTTP"]="80"
  ["HTTPS"]="443"
  ["Prometheus"]="9090"
  ["Grafana"]="3001"
  ["Loki"]="3100"
  ["Alertmanager"]="9093"
)

# Required .env variables (from .env.example)
REQUIRED_ENV_VARS=(
  "POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "POSTGRES_HOST" "POSTGRES_PORT"
  "REDIS_HOST" "REDIS_PORT" "REDIS_PASSWORD"
  "QDRANT_HOST" "QDRANT_PORT"
  "MINIO_ROOT_USER" "MINIO_ROOT_PASSWORD" "MINIO_HOST" "MINIO_PORT"
  "JWT_SECRET_KEY" "JWT_ALGORITHM" "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" "JWT_REFRESH_TOKEN_EXPIRE_DAYS"
  "ML_ENGINE_URL" "BASE_MODEL_NAME" "ML_DEVICE" "DEVICE"
  "CELERY_BROKER_URL" "CELERY_RESULT_BACKEND" "CELERY_WORKER_CONCURRENCY"
  "APP_ENV" "APP_SECRET_KEY"
  "BACKEND_PORT" "ML_ENGINE_PORT" "FRONTEND_PORT" "HTTP_PORT" "HTTPS_PORT"
  "NEXT_PUBLIC_API_URL"
  "OTEL_EXPORTER_OTLP_ENDPOINT"
)

# ─── Helpers ────────────────────────────────────────────────────────────────
log_info()    { echo -e "  ${CYAN}[INFO]${NC}  $1"; }
log_ok()      { echo -e "  ${GREEN}[OK]${NC}    $1"; }
log_fail()    { echo -e "  ${RED}[FAIL]${NC}  $1"; ((FAIL_COUNT++)); }
log_warn()    { echo -e "  ${YELLOW}[WARN]${NC}  $1"; ((WARN_COUNT++)); }
log_header()  { echo -e "\n${BOLD}$1${NC}"; echo "──────────────────────────────────────────────────────"; }
log_detail()  { if [ "$VERBOSE" = true ]; then echo "         $1"; fi; }

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    log_ok "$1 is installed ($(command -v "$1"))"
    return 0
  else
    log_fail "$1 is NOT installed"
    return 1
  fi
}

check_port() {
  local service="$1" port="$2"
  if netstat -an 2>/dev/null | grep -q "LISTEN.*:${port}[[:space:]]"; then
    log_detail "Port ${port} is already in use by another process"
    log_warn "Port ${port} (${service}) — already in use"
    return 1
  elif ss -tln 2>/dev/null | grep -q ":${port}[[:space:]]"; then
    log_detail "Port ${port} is already in use by another process"
    log_warn "Port ${port} (${service}) — already in use"
    return 1
  else
    log_ok "Port ${port} (${service}) is available"
    return 0
  fi
}

check_url() {
  local name="$1" url="$2"
  if curl -fs --max-time 5 "$url" >/dev/null 2>&1; then
    log_ok "${name} is reachable at ${url}"
    return 0
  else
    log_fail "${name} is NOT reachable at ${url}"
    return 1
  fi
}

# ─── Parse flags ────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --verbose|-v) VERBOSE=true ;;
    --ci)         CI_MODE=true ;;
    --help|-h)
      echo "Usage: $0 [--verbose] [--ci]"
      echo "  --verbose    Show detailed output"
      echo "  --ci         Exit immediately on first failure (CI mode)"
      exit 0
      ;;
  esac
done

if [ "$CI_MODE" = true ]; then
  set -e
fi

# ═════════════════════════════════════════════════════════════════════════════
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       VeriUnlearn — Deployment Validation Script           ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo " Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo " Project: ${PROJECT_DIR}"
echo ""

# ═════════════════════════════════════════════════════════════════════════════
# 1. Docker and Docker Compose
# ═════════════════════════════════════════════════════════════════════════════
log_header "1. Docker & Docker Compose"

DOCKER_VERSION=""
if command -v docker >/dev/null 2>&1; then
  DOCKER_VERSION=$(docker --version 2>/dev/null)
  log_ok "Docker installed: ${DOCKER_VERSION}"
else
  log_fail "Docker is NOT installed"
  if [ "$CI_MODE" = true ]; then exit 1; fi
fi

COMPOSE_VERSION=""
if docker compose version >/dev/null 2>&1; then
  COMPOSE_VERSION=$(docker compose version 2>/dev/null)
  log_ok "Docker Compose installed: ${COMPOSE_VERSION}"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_VERSION=$(docker-compose --version 2>/dev/null)
  log_warn "docker-compose (v1) installed: ${COMPOSE_VERSION}. Upgrade to v2."
else
  log_fail "Docker Compose is NOT installed"
  if [ "$CI_MODE" = true ]; then exit 1; fi
fi

# Check Docker daemon is running
if docker info >/dev/null 2>&1; then
  log_ok "Docker daemon is running"
else
  log_fail "Docker daemon is NOT running"
  if [ "$CI_MODE" = true ]; then exit 1; fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# 2. Docker Compose File
# ═════════════════════════════════════════════════════════════════════════════
log_header "2. Docker Compose Configuration"

if [ -f "$COMPOSE_FILE" ]; then
  log_ok "docker-compose.yml found at ${COMPOSE_FILE}"
  log_detail "Size: $(wc -c < "$COMPOSE_FILE") bytes"
else
  log_fail "docker-compose.yml NOT found at ${COMPOSE_FILE}"
  if [ "$CI_MODE" = true ]; then exit 1; fi
fi

# Validate syntax
if docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
  log_ok "docker-compose.yml syntax is valid"
else
  log_fail "docker-compose.yml has INVALID syntax"
  if [ "$VERBOSE" = true ]; then
    docker compose -f "$COMPOSE_FILE" config 2>&1 || true
  fi
  if [ "$CI_MODE" = true ]; then exit 1; fi
fi

# Check compose file consistency
BACKEND_PORT=$(grep -oP 'BACKEND_PORT[^}]*\K[0-9]+' "$COMPOSE_FILE" 2>/dev/null || echo "8000")
FRONTEND_PORT=$(grep -oP 'FRONTEND_PORT[^}]*\K[0-9]+' "$COMPOSE_FILE" 2>/dev/null || echo "3000")
ML_ENGINE_PORT=$(grep -oP 'ML_ENGINE_PORT[^}]*\K[0-9]+' "$COMPOSE_FILE" 2>/dev/null || echo "8001")
log_detail "Configured ports: backend=${BACKEND_PORT}, frontend=${FRONTEND_PORT}, ml-engine=${ML_ENGINE_PORT}"

# ═════════════════════════════════════════════════════════════════════════════
# 3. Port Availability
# ═════════════════════════════════════════════════════════════════════════════
log_header "3. Port Availability"

for service in "${!REQUIRED_PORTS[@]}"; do
  port="${REQUIRED_PORTS[$service]}"
  check_port "$service" "$port"
done

# ═════════════════════════════════════════════════════════════════════════════
# 4. Environment File
# ═════════════════════════════════════════════════════════════════════════════
log_header "4. Environment Configuration"

if [ -f "$ENV_FILE" ]; then
  log_ok ".env file found at ${ENV_FILE}"
  log_detail "Size: $(wc -c < "$ENV_FILE") bytes"
else
  log_fail ".env file NOT found at ${ENV_FILE}"
  log_detail "Copy from .env.example: cp .env.example .env"
fi

if [ -f "$ENV_EXAMPLE" ]; then
  log_ok ".env.example found at ${ENV_EXAMPLE}"
else
  log_fail ".env.example NOT found"
fi

# Check required variables
if [ -f "$ENV_FILE" ]; then
  log_info "Checking required environment variables..."
  source "$ENV_FILE" 2>/dev/null || true

  for var in "${REQUIRED_ENV_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
      # Check if variable exists in .env file (might be empty)
      if grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
        log_warn "Variable ${var} is set but EMPTY in .env"
      else
        log_fail "Required variable ${var} is MISSING from .env"
        if [ "$CI_MODE" = true ]; then exit 1; fi
      fi
    else
      # Mask secrets for display
      local display_val="${!var}"
      case "$var" in
        *PASSWORD*|*SECRET*|*KEY*|*TOKEN*)
          if [ "${#display_val}" -gt 8 ]; then
            display_val="${display_val:0:4}...${display_val: -4}"
          fi
          ;;
      esac
      log_detail "${var}=${display_val}"
    fi
  done
fi

# Check for default secrets warning
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE" 2>/dev/null || true
  if [[ "${JWT_SECRET_KEY:-}" == "dev-jwt-secret-key-at-least-32-chars-long!!" ]]; then
    log_warn "JWT_SECRET_KEY is using DEFAULT dev value — CHANGE for production!"
  fi
  if [[ "${APP_SECRET_KEY:-}" == "dev-app-secret-key-at-least-32-chars-long!!!" ]]; then
    log_warn "APP_SECRET_KEY is using DEFAULT dev value — CHANGE for production!"
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# 5. Running Service Connectivity
# ═════════════════════════════════════════════════════════════════════════════
log_header "5. Running Service Connectivity (if services are up)"

# Check if any services are running
RUNNING_SERVICES=$(docker compose ps --status running 2>/dev/null | tail -n +2 || true)
if [ -n "$RUNNING_SERVICES" ]; then
  log_info "Container status:"
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
  echo ""

  # Check individual services
  check_url "Backend"       "http://localhost:${BACKEND_PORT}/health"
  check_url "ML Engine"     "http://localhost:${ML_ENGINE_PORT}/health"
  check_url "Frontend"      "http://localhost:${FRONTEND_PORT}"
  check_url "Prometheus"    "http://localhost:9090/-/healthy"
  check_url "Grafana"       "http://localhost:3001/api/health"
else
  log_info "No running containers detected. Skipping service connectivity checks."
  log_info "Start the stack with: docker compose up -d"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 6. Database Connectivity
# ═════════════════════════════════════════════════════════════════════════════
log_header "6. Database Connectivity"

PG_CONTAINER=$(docker compose ps -q postgres 2>/dev/null || true)
if [ -n "$PG_CONTAINER" ] && [ "$(docker inspect -f '{{.State.Status}}' "$PG_CONTAINER" 2>/dev/null)" = "running" ]; then
  PG_USER="${POSTGRES_USER:-veriunlearn}"
  PG_DB="${POSTGRES_DB:-veriunlearn}"
  if docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" >/dev/null 2>&1; then
    log_ok "PostgreSQL is running and accepting connections"
  else
    log_fail "PostgreSQL is NOT responding"
  fi
else
  log_warn "PostgreSQL container not running — skipping database connectivity check"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 7. Redis Connectivity
# ═════════════════════════════════════════════════════════════════════════════
log_header "7. Redis Connectivity"

REDIS_CONTAINER=$(docker compose ps -q redis 2>/dev/null || true)
if [ -n "$REDIS_CONTAINER" ] && [ "$(docker inspect -f '{{.State.Status}}' "$REDIS_CONTAINER" 2>/dev/null)" = "running" ]; then
  REDIS_PASS="${REDIS_PASSWORD:-veriunlearn_secret}"
  if docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASS" ping 2>/dev/null | grep -q "PONG"; then
    log_ok "Redis is running and responding to PING"
  else
    log_fail "Redis is NOT responding"
  fi
else
  log_warn "Redis container not running — skipping Redis connectivity check"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 8. MinIO Connectivity
# ═════════════════════════════════════════════════════════════════════════════
log_header "8. MinIO Connectivity"

MINIO_CONTAINER=$(docker compose ps -q minio 2>/dev/null || true)
if [ -n "$MINIO_CONTAINER" ] && [ "$(docker inspect -f '{{.State.Status}}' "$MINIO_CONTAINER" 2>/dev/null)" = "running" ]; then
  if docker exec "$MINIO_CONTAINER" curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
    log_ok "MinIO is running and healthy"
  else
    log_fail "MinIO is NOT healthy"
  fi
else
  log_warn "MinIO container not running — skipping MinIO connectivity check"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 9. GPU Availability
# ═════════════════════════════════════════════════════════════════════════════
log_header "9. GPU Support"

if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null | head -1)
  log_ok "NVIDIA GPU detected: ${GPU_INFO}"
  log_detail "nvidia-smi available — GPU acceleration supported"
else
  log_warn "nvidia-smi not found — running without GPU support (ML Engine will use CPU)"
fi

# Check NVIDIA Container Toolkit
if docker info 2>/dev/null | grep -q "nvidia"; then
  log_ok "NVIDIA Container Toolkit is installed (Docker GPU support enabled)"
else
  log_warn "NVIDIA Container Toolkit may not be installed — GPU passthrough to containers unavailable"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 10. System Resources
# ═════════════════════════════════════════════════════════════════════════════
log_header "10. System Resources"

# Memory
if command -v free >/dev/null 2>&1; then
  MEM_TOTAL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}')
  MEM_AVAIL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $7}')
  log_detail "Memory: ${MEM_TOTAL} total, ${MEM_AVAIL} available"
fi

# Disk
DISK_INFO=$(df -h "$PROJECT_DIR" 2>/dev/null | tail -1)
DISK_AVAIL=$(echo "$DISK_INFO" | awk '{print $4}')
DISK_USED=$(echo "$DISK_INFO" | awk '{print $3}')
DISK_TOTAL=$(echo "$DISK_INFO" | awk '{print $2}')
log_detail "Disk: ${DISK_USED} / ${DISK_TOTAL} used, ${DISK_AVAIL} available"

# Check disk space
DISK_PCT=$(echo "$DISK_INFO" | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ] 2>/dev/null; then
  log_fail "Low disk space: ${DISK_PCT}% used"
elif [ "$DISK_PCT" -gt 80 ] 2>/dev/null; then
  log_warn "Disk space warning: ${DISK_PCT}% used"
else
  log_ok "Disk space: ${DISK_PCT}% used"
fi

# CPU info
if [ -f /proc/cpuinfo ]; then
  CPU_CORES=$(grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "N/A")
  log_detail "CPU cores: ${CPU_CORES}"
fi

# ═════════════════════════════════════════════════════════════════════════════
# 11. Git Status
# ═════════════════════════════════════════════════════════════════════════════
log_header "11. Git Status"

if command -v git >/dev/null 2>&1; then
  GIT_BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  GIT_COMMIT=$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
  GIT_TAG=$(git -C "$PROJECT_DIR" describe --tags --exact-match 2>/dev/null || echo "no tag")
  log_detail "Branch: ${GIT_BRANCH}"
  log_detail "Commit: ${GIT_COMMIT}"
  log_detail "Tag:    ${GIT_TAG}"

  # Check for uncommitted changes
  if git -C "$PROJECT_DIR" diff --quiet 2>/dev/null; then
    log_ok "Working directory is clean"
  else
    log_warn "Working directory has uncommitted changes"
    if [ "$VERBOSE" = true ]; then
      git -C "$PROJECT_DIR" status --short 2>/dev/null
    fi
  fi
else
  log_warn "Git not available"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
echo ""
log_header "Deployment Status Summary"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}✅ All checks passed.${NC}"
  echo -e "  ${GREEN}   The environment is ready for deployment.${NC}"
elif [ "$FAIL_COUNT" -eq 0 ] && [ "$WARN_COUNT" -gt 0 ]; then
  echo -e "  ${YELLOW}${BOLD}⚠️   ${FAIL_COUNT} failures, ${WARN_COUNT} warnings.${NC}"
  echo -e "  ${YELLOW}   Passed with warnings — review items above.${NC}"
else
  echo -e "  ${RED}${BOLD}❌ ${FAIL_COUNT} failures, ${WARN_COUNT} warnings.${NC}"
  echo -e "  ${RED}   Deployment validation FAILED.${NC}"
fi

echo ""
echo "  Duration: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

exit $FAIL_COUNT
