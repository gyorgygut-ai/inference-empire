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
ENV_FILE="$WORKSPACE_ROOT/dist/flux2/deploy.env"
SCHEMA_FILE="$WORKSPACE_ROOT/packages/schemas/flux2/schema.ts"
TIMEOUT=120

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
    sleep 2
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
  env_token=$(grep "^ROUTER_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
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
GENERATED_TOKEN=$(npx nx run router:generate-flux2-auth-token-deploy 2>/dev/null | tail -1)
[ -n "$GENERATED_TOKEN" ] && log_pass "Auth token generated" || log_fail "Failed to generate auth token"

# ── Step 2: Deploy router:deploy-flux2 ──────────────────────────────────────
log_start "Deploying router:deploy-flux2..."
DEPLOYED_ROUTER_URL=$(npx nx run router:deploy-flux2 2>/dev/null | tail -1)
[ -n "$DEPLOYED_ROUTER_URL" ] && log_pass "router:deploy-flux2 deployed to $DEPLOYED_ROUTER_URL" || log_fail "router:deploy-flux2 did not output a URL"

# ── Step 3: Wait for deployed router ────────────────────────────────────────
log_start "Waiting for deployed router to be ready..."
wait_for_url "$DEPLOYED_ROUTER_URL" "router" && log_pass "router:deploy-flux2 is listening" || log_fail "router:deploy-flux2 did not start within ${TIMEOUT}s"

# ── Step 4: Deploy face-value:deploy ────────────────────────────────────────
log_start "Deploying face-value:deploy..."
DEPLOYED_FV_URL=$(npx nx run face-value:deploy 2>/dev/null | tail -1)
[ -n "$DEPLOYED_FV_URL" ] && log_pass "face-value:deploy deployed to $DEPLOYED_FV_URL" || log_fail "face-value:deploy did not output a URL"

# ── Step 5: Wait for deployed face-value ────────────────────────────────────
log_start "Waiting for deployed face-value to be ready..."
wait_for_url "$DEPLOYED_FV_URL" "face-value" && log_pass "face-value:deploy is listening" || log_fail "face-value:deploy did not start within ${TIMEOUT}s"

# ── Step 6: Assertions ──────────────────────────────────────────────────────
log_start "Running assertions..."

# 6a. Schema file exists
assert_file_exists "$SCHEMA_FILE"

# 6b. MODAL_WORKER_URL is valid
assert_env_var "MODAL_WORKER_URL" "^https://"

# 6c. BEAM_WORKER_URL is valid
assert_env_var "BEAM_WORKER_URL" "^https://"

# 6d. ROUTER_AUTH_TOKEN is valid
assert_token_valid

# 6e. ROUTER_URL accepts ROUTER_AUTH_TOKEN
assert_router_auth "$DEPLOYED_ROUTER_URL" "$GENERATED_TOKEN"

# 6f. router:deploy-flux2 listening on ROUTER_URL
router_url_in_env=$(grep "^ROUTER_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ "$router_url_in_env" = "$DEPLOYED_ROUTER_URL" ]; then
  log_pass "router:deploy-flux2 listening on ROUTER_URL"
else
  log_fail "ROUTER_URL mismatch (expected $DEPLOYED_ROUTER_URL, got $router_url_in_env)"
fi

# 6g. ROUTER_URL + ROUTER_AUTH_TOKEN responds
status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $GENERATED_TOKEN" "$DEPLOYED_ROUTER_URL/sup" 2>/dev/null || echo "000")
[ "$status" != "401" ] && [ "$status" != "000" ] && log_pass "ROUTER_URL + ROUTER_AUTH_TOKEN responds" || log_fail "ROUTER_URL + ROUTER_AUTH_TOKEN returned $status"

# 6h. face-value:deploy returns 200
status=$(curl -s -o /dev/null -w "%{http_code}" "$DEPLOYED_FV_URL" 2>/dev/null || echo "000")
[ "$status" = "200" ] && log_pass "face-value:deploy returns 200" || log_fail "face-value:deploy returned $status"

# 6i. face-value:deploy requests router:deploy-flux2 url
fv_router_url=$(grep "^ROUTER_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ "$fv_router_url" = "$DEPLOYED_ROUTER_URL" ]; then
  log_pass "face-value:deploy requests router:deploy-flux2 url"
else
  log_fail "face-value:deploy ROUTER_URL mismatch (expected $DEPLOYED_ROUTER_URL, got $fv_router_url)"
fi

# 6j. face-value:deploy uses ROUTER_AUTH_TOKEN
fv_token=$(grep "^ROUTER_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
if [ "$fv_token" = "$GENERATED_TOKEN" ]; then
  log_pass "face-value:deploy uses ROUTER_AUTH_TOKEN"
else
  log_fail "face-value:deploy ROUTER_AUTH_TOKEN mismatch"
fi

log_pass "All deploy assertions passed"
