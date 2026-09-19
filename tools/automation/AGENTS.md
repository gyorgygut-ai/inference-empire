# Dirigera Local API Control

IKEA Dirigera hub local REST API (port 8443, HTTPS, self-signed cert). PKCE OAuth with physical button press.

## Kickoff: Connect Your Hub

1. **Discover hub IP** — `nx run automation:find` (mDNS → ARP → port scan)
2. **Authenticate** — `nx run automation:auth`
   - Generates PKCE challenge
   - Prompts: "Press the hub button once, then press Enter"
   - Saves token to **macOS Keychain** (service: `automation`, account: your user)
3. **Test connection** — `nx run automation:api -- GET /v1/devices`
4. **Control lights** — `nx run automation:api -- PATCH /v1/devices/{id} '{"attributes":{"isOn":true}}'`

## Token Storage

- **Primary:** macOS Keychain (`security find-generic-password -s automation`)
- **Fallback:** `~/.config/automation/token.json` (chmod 600)
- JWT expiry: ~10 years (per `exp` claim)
- Re-run `auth` if token ever invalidated

## Scripts (in `tools/automation/`)

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

## Coding Rules (for future TS work in tools/automation/)

- **Short functions** — single responsibility, <20 lines ideal
- **Explicit naming** — `turnOnKitchenLights()` not `doThing()`
- **Functional style** — prefer `.map()`, `.filter()`, `.reduce()` over `for`/`while` loops
- **No imperative mutations** — avoid `let` + push; use `const` + transformations
- **Type everything** — no `any`, explicit return types on public functions
- **Pure where possible** — separate IO (fetch, Keychain) from logic
- **Error as values** — `Result<T, E>` or `Option<T>` over throwing

## API Reference

### GET Endpoints

| Endpoint | Payload | Returns |
|----------|---------|---------|
| `/v1/devices` | — | All devices with full attributes, capabilities, room, deviceSet, remoteLinks |
| `/v1/devices/{id}` | — | Single device detail (attributes: isOn, lightLevel, colorTemperature, colorHue, colorSaturation, batteryPercentage, isDetected, isOpen, etc.) |
| `/v1/rooms` | — | Rooms: [{id, name, color, icon}] — 7 rooms: Staircase, Bedroom, Bathroom, Rooftop, Kitchen, Hall, Living room |
| `/v1/scenes` | — | Scenes: [{id, info: {name, icon}, type: customScene\|userScene, triggers, actions, commands, lastTriggered}] |
| `/v1/health` | — | Hub health status |

### POST Endpoints

| Endpoint | Payload | Returns |
|----------|---------|---------|
| `/v1/oauth/authorize` | Query params: `audience=homesmart.local`, `response_type=code`, `code_challenge={S256}`, `code_challenge_method=S256` | `{code}` or `{error}` |
| `/v1/oauth/token` | Body: `code_verifier={}`, `code={}`, `name={hostname}`, `grant_type=authorization_code` | `{access_token}` |

### PATCH Endpoints

| Endpoint | Payload | Does |
|----------|---------|------|
| `/v1/devices/{id}` | `{"attributes":{"isOn":true}}` | Turn device on |
| `/v1/devices/{id}` | `{"attributes":{"isOn":false}}` | Turn device off |
| `/v1/devices/{id}` | `{"attributes":{"lightLevel":127}}` | Set brightness 0–254 (0=off) |
| `/v1/devices/{id}` | `{"attributes":{"colorTemperature":2202}}` | Set white temperature (check `colorTemperatureMin`/`Max` per bulb, e.g. 2202–4000K) |
| `/v1/devices/{id}` | `{"attributes":{"colorHue":21845,"colorSaturation":80}}` | Set color (hue 0–65535, sat 0–100) |
| `/v1/devices/{id}` | `{"attributes":{"customName":"Kitchen Lamp"}}` | Rename device |
| `/v1/devices/{id}` | `{"attributes":{"childLock":true}}` | Enable child lock (outlets) |
| `/v1/devices/{id}` | `{"attributes":{"statusLight":false}}` | Disable LED status indicator (outlets) |
| `/v1/devices/{id}` | `{"attributes":{"startupOnOff":"startOff"}}` | Set power-on behavior: `startOn`/`startOff`/`startPrevious` |
| `/v1/scenes/{id}` | `{"actions":[], "commands":[...]}` | Trigger/modify scene (type-dependent) |

### Device Attribute Index

| Attribute | Type | Range | On Device Types |
|-----------|------|-------|-----------------|
| `isOn` | bool | — | lights, outlets, controllers, sensors |
| `lightLevel` | int | 0–254 | lights, outlets |
| `colorTemperature` | int | bulb-dependent (e.g. 2202–4000) | white-tunable bulbs |
| `colorHue` | int | 0–65535 | CWS (color) bulbs |
| `colorSaturation` | int | 0–100 | CWS bulbs |
| `batteryPercentage` | int | 0–100 | sensors, controllers |
| `isDetected` | bool | — | motion sensors |
| `isOpen` | bool | — | door/window sensors |
| `lightLevel` (sensors) | int | 1–5 | motion sensors (ambient light) |
| `isReachable` | bool | — | all devices (read-only) |

### Key Device IDs

| Device | ID | Type | Room |
|--------|----|----|----|
| Sensor downstairs | `0e5efacf-4a95-4e3a-b9df-81a88cd64836_1` | motionSensor | Staircase |
| Sensor hall | `d735707f-05dc-47bc-8b81-7a04ad347b49_1` | motionSensor | Hall |
| Sensor upstairs | `5eff3018-c4ec-4a63-8779-f8895db8f405_1` | motionSensor | Staircase (battery: 1%, unreachable) |
| Sensor Fridge Door | `9e26b14b-591c-4a48-810e-4697e36562c7_1` | openCloseSensor | Kitchen |
| Shortcut button | `ebf8b8dd-081c-41c8-ba9b-f969b63312b0_1` | shortcutController | Living room |
| Plug 1 | `dee49759-bb38-4a48-a048-b193d5128dbf_1` | outlet | Living room |
| Hall pendant | `7b3bad7e-f6c4-4197-82e2-031eb4edfb4a_1` | TRADFRIbulbE27WS | Hall (warm/white only) |
| Staircase bulb | `6f78552b-687d-43e4-ab8a-994b722ca79c_1` | TRADFRI E27 CWS | Staircase (color) |
| Living room GU10 #1 | `eb6623f9-c1f8-4830-b4fb-5b29f92c43e7_1` | TRADFRI GU10 CWS | Living room (color) |
| Living room GU10 #2 | `2deca4ae-eb4d-45b3-b022-3c90475ca8a9_1` | TRADFRI GU10 CWS | Living room (color) |
| Kitchen GU10 | `e6cef233-7b27-466d-9c28-e6f7947822e4_1` | TRADFRI GU10 CWS | Kitchen (color) |
