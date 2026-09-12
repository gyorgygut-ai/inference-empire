# Workers — collapsible status list (no chat link)

## Source
- Built manifest `src/lib/manifest.json` from `scripts/build-manifest.mjs` reading only `../workers/**/worker_*.py` (`worker_{beam|flash|modal}_{tq|cls|eq|asgi}_{model}.py` per `../workers/AGENTS.md:26-37`) — stem alone gives `platform` + `pattern` + `model` (contract key)

## UI
- Location: `src/components/panels/Workers.tsx:9-21` inside `CollapsiblePanel side="left"` (`src/components/ui/CollapsiblePanel.tsx:35-51`)
- Accordions by model/type (5 groups) outer, variants inner with chip `platform/pattern` + status dot
- Keep `src/components/layout/AppShell.tsx:9-27` reducer as-is; if mismatches `AGENTS.md:21-30` update spec not code
- No chat coupling

## Status
- `src/app/api/workers/status/route.ts` (Node `fetch`, server-only, hides keys) — reads `src/lib/manifest.json`, groups by `platform`, probes provider REST (no Python import):
  - Beam: `GET https://api.beam.cloud/v2/...` with `Authorization: Bearer ${BEAM_TOKEN}` per `https://docs.beam.cloud/v2/reference/api-docs/tasks/tasks-status` and `https://api.beam.cloud` base — `stub_id` derived from `worker_name()` regex `../workers/e2e_targets.py:33-36`
  - Runpod (Flash): `GET https://api.runpod.io/v2/endpoints` + `GET https://api.runpod.io/v2/endpoints/{id}/health` with `Authorization: Bearer ${RUNPOD_API_KEY}` per `https://docs.runpod.io/api-reference-v2/overview` (base `https://api.runpod.io/v2`)
  - Modal: `GET https://api.modal.com/...` with `MODAL_TOKEN_ID/SECRET` (fallback `unknown` if undocumented)
- Maps `2xx`→`healthy`, `4xx`→`deployed`, `5xx/timeout`→`unhealthy`, missing `*_TOKEN`/`*_KEY`→`unknown`
- Fallback `unknown` when keys unset — route is optional, panel still renders 22 workers with chip `platform/pattern` even when all `unknown`

## Mapping
Per `AGENTS.md:32-39` flat list.

## Sync
Via `01-sync.md` — reads `src/lib/manifest.json` built by `scripts/build-manifest.mjs` (runs on `prebuild`/`predev` in `package.json:5`), shared with Chat.

## Touched
- reads `src/lib/manifest.json` (built, not hand-written)
- edit `src/components/panels/Workers.tsx`
- optional `src/app/api/workers/status/route.ts` (server platform list via SDK/CLI + keys from `.env`)
