# WebRTC Bench

Vue + TypeScript app for the WebRTC worker.

---

## Dev ENV

**env**:
  - `PORT`: `${DEV_WEBRTC_BENCH_PORT}`
  - `VITE_WEBRTC_WORKER_URL`: `http://127.0.0.1:${DEV_WEBRTC_WORKER_PORT}`

**NX**:
  - **Cmd**: `npx vite --host 127.0.0.1 --port="$PORT"`
  - **Readiness**: `{ continuous, readyWhen: { url: "http://127.0.0.1:{env.DEV_WEBRTC_BENCH_PORT}" }}`
  - **Depends**: `worker-webrtc:dev` + `"waitFor": "ready"`

---

## STRUCTURE

- `App.vue`: renders the worker probes in test order
- `main.ts`: mounts `App.vue`
- `components/`: generic action card, primary button, and action result
- `worker/WorkerServeProbe.vue`: probes the configured worker health URL
- `worker/OfferAnswerProbe.vue`: submits an SDP offer and displays the answer
- `worker/TurnConnectionProbe.vue`: verifies the shared browser session uses a relay
- `worker/ArbitraryDataProbe.vue`: sends JSON and displays the response
- `worker/ClientIsolationProbe.vue`: verifies concurrent clients receive isolated responses
- `worker/InvalidInputProbe.vue`: submits invalid input and displays the rejection
- `worker/RealtimeInterruptProbe.vue`: interrupts an in-progress data-channel response
- `worker/ConnectionFailureProbe.vue`: verifies failure containment and recovery
- `worker/WorkerProbeCard.vue`: shared action-card presentation
- `worker/client-session.ts`: owns the shared peer connection for one browser client
- `worker/useProbe.ts`: handles action loading and results

---

## SPECS

**Probe: Serve**:

- **Problem**: The worker must serve on `$PORT`
- **Acceptance**:
  - Card layout
  - Displays worker url
  - Displays send button
  - Disabled during fetch
  - Displays last response

**Probe: Offer Answer**:

- **Problem**: The worker must accept an SDP offer and return an answer.
- **Acceptance**:
  - Card layout
  - Displays worker url
  - Displays send button
  - Disabled during negotiation
  - Displays the SDP answer or failure

**Probe: TURN Connection**:

- **Problem**: The worker must establish a data-channel connection through TURN.
- **Acceptance**:
  - Card layout
  - Displays worker url
  - Uses relay-only ICE policy
  - Displays send button
  - Disabled during connection
  - Displays whether the shared session uses a relay candidate

**Probe: Arbitrary Data**:

- **Problem**: The worker must accept arbitrary schema-valid JSON and return a response.
- **Acceptance**:
  - Card layout
  - Displays the input and worker url
  - Displays send button
  - Disabled during request
  - Displays the returned output
  - Keeps the response isolated to the sending browser client

**Probe: Client Isolation**:

- **Problem**: Concurrent browser clients must receive only their own responses.
- **Acceptance**:
  - Card layout
  - Displays worker url
  - Displays send button
  - Disabled during requests
  - Displays both distinct client responses

**Probe: Invalid Input**:

- **Problem**: The worker must reject invalid data-channel input.
- **Acceptance**:
  - Card layout
  - Displays send button
  - Disabled during request
  - Displays the rejection response
  - Keeps the shared client session usable

**Probe: Realtime Interrupt**:

- **Problem**: A browser client must interrupt an in-progress response.
- **Acceptance**:
  - Card layout
  - Displays worker url
  - Displays send button
  - Disabled during stream and interruption
  - Displays the interrupted response and confirms the session remains usable

**Probe: Connection Failure**:

- **Problem**: The worker must contain a failed connection to its client session.
- **Acceptance**:
  - Card layout
  - Displays send button
  - Disabled during connection failure and recovery
  - Displays the surviving client response and recovered response
  - Does not interrupt another browser client
