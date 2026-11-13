# WebRTC Worker

Realtime HTTP service for WebRTC; not a GPU inference worker.

---

## Dev ENV

**env**:
  - `WORKER_WEBRTC_PORT`: `${DEV_WEBRTC_WORKER_PORT}`

**NX**:
  - **Cmd**: `npx tsx apps/workers/webrtc/src/server.ts`
  - **Readiness**: `{ continuous, readyWhen: { url: "http://127.0.0.1:{env.DEV_WEBRTC_WORKER_PORT}" }}`
  - **Testing**: `test-unit` checks the health response; `test-unit:watch` watches the same test
  - **Lint**: `lint`

## Structure: `./src/`

- `server.ts`: serves the health response on `WORKER_WEBRTC_PORT`
- `./tests/server.test.ts`: verifies the configured port responds
