# Fix push-router-env.mjs — read Vercel creds from .vercel/project.json and vercel CLI

## Problem
The script only reads `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` from env vars. These are set in CI from GitHub secrets, but not locally. The script skips with "Vercel env vars not set; skipping Vercel push (local dev ok)".

## Solution
Update `apps/face-value/scripts/push-router-env.mjs` to:

1. Remove `VERCEL_ORG_ID` from early-exit check (it's never used)
2. Read `VERCEL_PROJECT_ID` from `.vercel/project.json` if not in env vars
3. Read `VERCEL_TOKEN` from env vars first, then fall back to `vercel token` CLI command
4. Exit 0 with graceful message if credentials are still absent

## Changes to `push-router-env.mjs`

### Before (lines 14-21):
```javascript
const VERCEL_TOKEN = process.env.VERCEL_TOKEN
const VERCEL_ORG_ID = process.env.VERCEL_ORG_ID
const VERCEL_PROJECT_ID = process.env.VERCEL_PROJECT_ID

if (!VERCEL_TOKEN || !VERCEL_ORG_ID || !VERCEL_PROJECT_ID) {
  console.log("[push-router-env] Vercel env vars not set; skipping Vercel push (local dev ok)")
  process.exit(0)
}
```

### After:
```javascript
const workspaceRoot = process.cwd()
const projectRoot = join(workspaceRoot, "apps", "face-value")

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

// Read VERCEL_PROJECT_ID from env vars or .vercel/project.json
let VERCEL_PROJECT_ID = process.env.VERCEL_PROJECT_ID
if (!VERCEL_PROJECT_ID) {
  const projectJsonPath = join(projectRoot, ".vercel", "project.json")
  if (existsSync(projectJsonPath)) {
    const projectJson = JSON.parse(readFileSync(projectJsonPath, "utf-8"))
    VERCEL_PROJECT_ID = projectJson.projectId
  }
}

if (!VERCEL_PROJECT_ID) {
  console.log("[push-router-env] VERCEL_PROJECT_ID not found; skipping Vercel push (local dev ok)")
  process.exit(0)
}
```

### Also move `workspaceRoot` declaration before it's used
Line 23 currently has `const workspaceRoot = process.cwd()` — move this to the top with the other credential reads.

## Verification
After changes:
1. Script reads `.vercel/project.json` for project ID (already committed to repo)
2. Script reads `vercel token` CLI for auth token (if `vercel login` was done)
3. In CI: env vars from GitHub secrets take priority (no change)
4. Locally: falls back to `.vercel/project.json` + `vercel token`
5. Run `node scripts/push-router-env.mjs` from `apps/face-value/` to test