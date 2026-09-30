# Fix push-router-env.mjs to read VERCEL_TOKEN from Vercel CLI auth config

## Problem
`push-router-env.mjs` needs a `VERCEL_TOKEN` to call the Vercel API. The current code uses `execSync("vercel token")` which doesn't output the token.

## Solution
Update `apps/face-value/scripts/push-router-env.mjs` to read `VERCEL_TOKEN` from Vercel's CLI auth config:

### Vercel CLI auth config locations
- **macOS**: `~/Library/Application Support/com.vercel.cli/auth.json`
- **Linux**: `~/.vercel/auth.json`

### Auth file structure
```json
{
  "token": "vca_2HvMlJ5WbQVz01dC226tDBqcUVIRGemFh44upQ31Y9N71xAZvd1VEY1z",
  "userId": "fu4DGF1UrpAuZFN3DRMZEa6S",
  "refreshToken": "vcr_50UbqoWOaApUsZktFKuZ9hwGqvKDCb3z7ooyd95qfONuWX8NYP41d8yA",
  "expiresAt": 1790799926
}
```

### Changes to `push-router-env.mjs`

**Before (lines 17-27):**
```javascript
// Read VERCEL_TOKEN from env vars or vercel CLI
let VERCEL_TOKEN = process.env.VERCEL_TOKEN
if (!VERCEL_TOKEN) {
  try {
    VERCEL_TOKEN = execSync("vercel token", { encoding: "utf8", stdio: ["pipe", "pipe", "ignore"] }).trim()
  }
  catch {
    console.log("[push-router-env] VERCEL_TOKEN not found in env or vercel CLI; skipping Vercel push (local dev ok)")
    process.exit(0)
  }
}
```

**After:**
```javascript
// Read VERCEL_TOKEN from env vars or Vercel CLI auth config
let VERCEL_TOKEN = process.env.VERCEL_TOKEN
if (!VERCEL_TOKEN) {
  const authPath = process.platform === "darwin"
    ? join(process.env.HOME, "Library", "Application Support", "com.vercel.cli", "auth.json")
    : join(process.env.HOME, ".vercel", "auth.json")
  if (existsSync(authPath)) {
    try {
      const authConfig = JSON.parse(readFileSync(authPath, "utf-8"))
      VERCEL_TOKEN = authConfig.token
    }
    catch { /* ignore */ }
  }
}

if (!VERCEL_TOKEN) {
  console.log("[push-router-env] VERCEL_TOKEN not found; skipping Vercel push (local dev ok)")
  process.exit(0)
}
```

## Verification Steps
1. After edit: `cd apps/face-value && node scripts/push-router-env.mjs` should output `[push-router-env] Upserted FLUX2_ROUTER_URL → Vercel (production+preview)`
2. Run `npx nx run face-value:dev` — verify `http://localhost:3000/` returns 200
3. Run `npx nx run face-value:deploy` — verify full deploy chain succeeds
4. Push and verify CI passes