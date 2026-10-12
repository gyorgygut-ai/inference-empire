# Dirigera Local API Control

IKEA Dirigera hub local REST API (port 8443, HTTPS, self-signed cert). PKCE OAuth with physical button press.

## Kickoff: Connect Your Hub

1. **Discover hub IP** — `nx run automation:find` (mDNS → ARP → port scan)
2. **Authenticate** — `nx run automation:auth`
   - Generates PKCE challenge
   - Prompts: "Press the hub button once, then press Enter"
   - Saves token to **macOS Keychain** (service: `automation`, account: your user)
3. **Test connection** — `nx run automation:api -- GET /v1/devices`
4. **Control lights** — `nx run automation:api -- PATCH /v1/devices/{id} '[{"attributes":{"isOn":true}}]'`

## Token Storage

- **Primary:** macOS Keychain (`security find-generic-password -s automation`)
- **Fallback:** `~/.config/automation/token.json` (chmod 600)
- Re-run `auth` if token ever invalidated

## Scripts (in `packages/automation/`)

| Script | Purpose |
|--------|---------|
| `automation-auth.sh` | PKCE OAuth flow → saves token to Keychain |
| `automation` | Authenticated REST client (GET/PATCH/POST/DELETE) |
| `automation-find` | Hub discovery via mDNS/ARP/port scan |

## Working Endpoints

| Method | Path | Use |
|--------|------|-----|
| GET | `/v1/devices` | List all devices |
| GET | `/v1/scenes` | List scenes |
| GET | `/v1/rooms` | List rooms |
| GET | `/v1/health` | Health check |
| PATCH | `/v1/devices/{id}` | Control device (attributes) |

**PATCH format:** body must wrap attributes in a list: `[{"attributes":{...}}]`. Bare `{"attributes":{...}}` returns 500.
