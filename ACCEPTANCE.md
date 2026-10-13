Acceptance: router-flux2:dev full chain

Superseded by `apps/router/tests/acceptance-dev.e2e.spec.ts`, run via:

- Cold: `rm -rf dist` from repo root
- Foreground, repo root: `npm exec nx run router:router-flux2:dev`
- Second terminal: `npm exec nx run router:test-e2e --configuration=dev`

The spec reads `ROUTER_URL` + `ROUTER_SECRET_AUTH_TOKEN` from
`dist/router-flux2/dev/` bare files, runs the auth matrix, then proves 2 Flux
images (`POST /q` + `GET /sup`, `modal:fc-*` task ids, presigned URLs curl to
`image/png` above 50KB) using `apps/router/generated/api.ts` types
(`AddToQueueRequest`, `AddToQueueResponse`, `SupResponse`).
