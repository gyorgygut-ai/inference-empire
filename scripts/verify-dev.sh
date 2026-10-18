#!/usr/bin/env bash
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Logging ─────────────────────────────────────────────────────────────────
log_start() { echo -e "${YELLOW}🚀 $1${NC}"; }
log_pass()  { echo -e "${GREEN}✅ $1${NC}"; }
log_fail()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ── Config ──────────────────────────────────────────────────────────────────
WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$WORKSPACE_ROOT/dist/flux2/dev.env"
SCHEMA_FILE="$WORKSPACE_ROOT/packages/schemas/flux2/schema.ts"
ROUTER_URL="http://127.0.0.1:5050"
FACE_VALUE_URL="http://127.0.0.1:3000"
TIMEOUT=60

# ── Background PIDs ─────────────────────────────────────────────────────────
PIDS=()

cleanup() {
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

# ── Helpers ─────────────────────────────────────────────────────────────────
wait_for_url() {
  local url="$1"
  local label="$2"
  local start
  start=$(date +%s)
  while true; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -qE "^[0-9]"; then
      return 0
    fi
    if [ $(($(date +%s) - start)) -ge "$TIMEOUT" ]; then
      return 1
    fi
    sleep 1
  done
}

assert_file_exists() {
  local file="$1"
  [ -f "$file" ] && log_pass "$file exists" || log_fail "$file not found"
}

assert_env_var() {
  local var="$1"
  local pattern="$2"
  local value
  value=$(grep "^${var}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
  if [ -n "$value" ] && echo "$value" | grep -qE "$pattern"; then
    log_pass "$var is valid"
  else
    log_fail "$var missing or invalid"
  fi
}

assert_token_valid() {
  local env_token
  env_token=$(grep "^ROUTER_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
  if [ -n "$env_token" ]; then
    log_pass "ROUTER_AUTH_TOKEN is valid"
  else
    log_fail "ROUTER_AUTH_TOKEN missing or empty"
  fi
}

assert_router_auth() {
  local url="$1"
  local token="$2"
  local status_no_auth status_with_auth
  status_no_auth=$(curl -s -o /dev/null -w "%{http_code}" "$url/sup" 2>/dev/null || echo "000")
  status_with_auth=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $token" "$url/sup" 2>/dev/null || echo "000")
  if [ "$status_no_auth" = "401" ] && [ "$status_with_auth" != "401" ]; then
    log_pass "Router accepts ROUTER_AUTH_TOKEN"
  else
    log_fail "Router auth check failed (no-auth=$status_no_auth, with-auth=$status_with_auth)"
  fi
}

# ── Step 1: Generate auth token ─────────────────────────────────────────────
log_start "Generating auth token..."
GENERATED_TOKEN=$(npx nx run router:generate-flux2-auth-token-dev 2>/dev/null | tail -1)
[ -n "$GENERATED_TOKEN" ] && log_pass "Auth token generated" || log_fail "Failed to generate auth token"

# ── Step 2: Start router:dev-flux2 ──────────────────────────────────────────
log_start "Starting router:dev-flux2..."
nohup npx nx run router:dev-flux2 > /tmp/verify-dev-router.log 2>&1 < /dev/null &
PIDS+=($!)
disown

# ── Step 3: Start face-value:dev ────────────────────────────────────────────
log_start "Starting face-value:dev..."
nohup npx nx run face-value:dev > /tmp/verify-dev-face-value.log 2>&1 < /dev/null &
PIDS+=($!)
disown

# ── Step 4: Wait for both to be ready ───────────────────────────────────────
log_start "Waiting for router:dev-flux2 to be ready..."
wait_for_url "$ROUTER_URL" "router" && log_pass "router:dev-flux2 is listening" || log_fail "router:dev-flux2 did not start within ${TIMEOUT}s"

log_start "Waiting for face-value:dev to be ready..."
wait_for_url "$FACE_VALUE_URL" "face-value" && log_pass "face-value:dev is listening" || log_fail "face-value:dev did not start within ${TIMEOUT}s"

# ── Step 5: Assertions ──────────────────────────────────────────────────────
log_start "Running assertions..."

# 5a. Schema file exists
assert_file_exists "$SCHEMA_FILE"

# 5b. MODAL_WORKER_URL is valid
assert_env_var "MODAL_WORKER_URL" "^https://"

# 5c. BEAM_WORKER_URL is valid
assert_env_var "BEAM_WORKER_URL" "^https://"

# 5d. ROUTER_AUTH_TOKEN is valid
assert_token_valid

# 5e. Router accepts ROUTER_AUTH_TOKEN
ROUTER_URL_FROM_ENV=$(grep "^ROUTER_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
assert_router_auth "$ROUTER_URL_FROM_ENV" "$GENERATED_TOKEN"

# 5f. face-value:dev returns 200
status=$(curl -s -o /dev/null -w "%{http_code}" "$FACE_VALUE_URL" 2>/dev/null || echo "000")
[ "$status" = "200" ] && log_pass "face-value:dev returns 200" || log_fail "face-value:dev returned $status"

# 5g. face-value:dev requests router:dev-flux2 url
router_url_in_env=$(grep "^ROUTER_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ "$router_url_in_env" = "$ROUTER_URL" ]; then
  log_pass "face-value:dev requests router:dev-flux2 url"
else
  log_fail "face-value:dev ROUTER_URL mismatch (expected $ROUTER_URL, got $router_url_in_env)"
fi

# 5h. face-value:dev uses ROUTER_AUTH_TOKEN
fv_token=$(grep "^ROUTER_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ -n "$fv_token" ]; then
  log_pass "face-value:dev uses ROUTER_AUTH_TOKEN"
else
  log_fail "face-value:dev ROUTER_AUTH_TOKEN missing"
fi

log_pass "All dev assertions passed"
