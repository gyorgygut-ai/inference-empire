#!/usr/bin/env bash
# dirigera-auth.sh - obtain and store a Dirigera API bearer token (PKCE OAuth)
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
HUB="${DIRIGERA_HUB:-192.168.1.64}"
PORT=8443
CLIENT_ID="${DIRIGERA_CLIENT_ID:-Shortcuts_PCC}"
TOKEN_FILE="${DIRIGERA_TOKEN_FILE:-$SCRIPT_DIR/.dirigera_token}"
BASE="https://${HUB}:${PORT}"

command -v jq >/dev/null || { echo "jq required (brew install jq)"; exit 1; }

echo "==> PKCE verifier + S256 challenge"
code_verifier=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-43)
code_challenge=$(printf '%s' "$code_verifier" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=')

echo "==> Requesting authorization code (GET with query params)..."

code=""
for attempt in 1 2 3; do
  resp=$(curl -k -f -s -m 15 -G "$BASE/v1/oauth/authorize" \
    --data-urlencode "audience=homesmart.local" \
    --data-urlencode "response_type=code" \
    --data-urlencode "code_challenge=$code_challenge" \
    --data-urlencode "code_challenge_method=S256" 2>&1) || {
    echo "    Attempt $attempt: curl failed (HTTP error or timeout)"
    echo "    Response: $resp"
    [ $attempt -lt 3 ] && { sleep $((2**attempt)); continue; } || { echo "All authorize attempts failed"; exit 1; }
  }

  if printf '%s' "$resp" | jq -e . >/dev/null 2>&1; then
    code=$(printf '%s' "$resp" | jq -r '.code // empty')
    if [ -n "$code" ]; then
      break
    fi
    error=$(printf '%s' "$resp" | jq -r '.error // empty')
    if [ "$error" = "Already one ongoing pairing request" ]; then
      echo "    Attempt $attempt: $error - waiting 30s before retry..."
      [ $attempt -lt 3 ] && { sleep 30; continue; }
    fi
    echo "    Attempt $attempt: no 'code' in response: $resp"
  else
    echo "    Attempt $attempt: invalid JSON response: $resp"
  fi

  [ $attempt -lt 3 ] && { sleep $((2**attempt)); continue; } || { echo "All authorize attempts failed"; exit 1; }
done

[ -n "$code" ] || { echo "No code received after 3 attempts"; exit 1; }
echo "    code: $code"

echo ""
echo "============================================================"
echo "  PRESS THE ACTION BUTTON ON THE DIRIGERA HUB ONCE"
echo "  (small button on the side of the hub - SHORT PRESS)"
echo "  THEN IMMEDIATELY PRESS ENTER HERE"
echo "============================================================"
read -r -p "Press the hub button now, then press Enter... " _

echo ""
echo "==> Requesting token (will retry for ~10 seconds)..."

token=""
for attempt in $(seq 1 5); do
  tok_resp=$(curl -k -f -s -m 15 -X POST "$BASE/v1/oauth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "code_verifier=$code_verifier" \
    --data-urlencode "code=$code" \
    --data-urlencode "name=$(hostname)" \
    --data-urlencode "grant_type=authorization_code" 2>&1) || {
    echo "    Attempt $attempt: token request failed (HTTP error)"
    echo "    Response: $tok_resp"
    [ $attempt -lt 5 ] && { sleep 2; continue; } || { echo "All token attempts failed"; exit 1; }
  }

  if ! printf '%s' "$tok_resp" | jq -e . >/dev/null 2>&1; then
    echo "    Attempt $attempt: invalid JSON from token endpoint: $tok_resp"
    [ $attempt -lt 5 ] && { sleep 2; continue; } || { echo "All token attempts failed"; exit 1; }
  fi

  token=$(printf '%s' "$tok_resp" | jq -r '.access_token // empty')
  [ -n "$token" ] && break
  
  error=$(printf '%s' "$tok_resp" | jq -r '.error // .error_description // empty')
  echo "    Attempt $attempt: $error"
  [ $attempt -lt 5 ] && { sleep 2; continue; } || { echo "All token attempts failed"; exit 1; }
done

[ -n "$token" ] || { echo "No token received after 5 attempts"; exit 1; }

security add-generic-password \
  -a "$USER" \
  -s "automation" \
  -w "$token" \
  -T "" \
  -U
echo "==> Token saved to macOS Keychain (service: automation)"