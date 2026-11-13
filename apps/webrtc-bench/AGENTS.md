# WebRTC Bench

Vue + TypeScript app for the WebRTC worker.

---

## Dev ENV

**env**:
  - `PORT`: `${DEV_WEBRTC_BENCH_PORT}`

**NX**:
  - **Cmd**: `npx vite --host 127.0.0.1 --port="$PORT"`
  - **Readiness**: `{ continuous, readyWhen: { url: "http://127.0.0.1:{env.DEV_WEBRTC_BENCH_PORT}" }}`
  - **Depends**: `worker-webrtc:dev` + `"waitFor": "ready"`

## Structure: `./src/`

- `App.vue`: renders `<div>Hello world</div>`
- `main.ts`: mounts `App.vue`
