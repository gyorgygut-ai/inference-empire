# WebRTC Worker

Realtime HTTP service for WebRTC; not a GPU inference worker.

---

## Dev ENV

**env**:
  - `PORT`: `${DEV_WEBRTC_WORKER_PORT}`
  - `SECRET_HUGGINGFACE_TOKEN`: `${SECRET_HUGGINGFACE_TOKEN}`

**NX**:
  - **Cmd**: `npx tsx apps/workers/webrtc/src/server.ts`
  - **Readiness**: `{ continuous, readyWhen: { url: "http://127.0.0.1:{env.DEV_WEBRTC_WORKER_PORT}" }}`
  - **Testing**: `test-unit` runs the worker behavior tests; `test-unit:watch` watches them
  - **Lint**: `lint`

---

## STRUCTURE

- `src/server.ts`: serves health, TURN configuration, SDP signaling, and isolated data-channel sessions
- `tests/serve.test.ts`: verifies health and CORS
- `tests/offer-answer.test.ts`: verifies SDP offer/answer negotiation
- `tests/turn-connection.test.ts`: verifies a relayed data-channel connection
- `tests/arbitrary-data.test.ts`: verifies JSON input/output
- `tests/client-isolation.test.ts`: verifies concurrent clients receive isolated output
- `tests/invalid-input.test.ts`: verifies invalid data-channel messages are rejected
- `tests/realtime-interrupt.test.ts`: verifies an in-progress response can be interrupted
- `tests/connection-failure.test.ts`: verifies one failed session does not affect another
- `dist/webrtc.schema.ts`: generated data-channel contract
- `packages/schemas/workers/webrtc.schema.json`: source data-channel contract

---

## SPECS

**Serve**:

- **Problem**: The worker must serve on `$PORT`
- **Acceptance**:
  - `:dev` serves
  - CORS allows all

**Negotiation: Offer Answer**:

- **Problem**: WebRTC clients need to negotiate a data-channel connection with the worker.
- **Acceptance**:
  - Accept a valid SDP offer and return a valid SDP answer.
  - Reject an invalid offer without creating a usable session.
- **Outcome**: Clients can establish a WebRTC data-channel session through the worker.

**Transport: TURN**:

- **Problem**: Clients need a relayed connection when direct ICE connectivity is unavailable.
- **Acceptance**:
  - Obtain short-lived Cloudflare TURN credentials from `https://fastrtc-turn-service.hf.space/credentials` using `SECRET_HUGGINGFACE_TOKEN`.
  - Return only the short-lived TURN configuration to the client.
  - Prove a relay-only connection using a relay candidate.
- **Outcome**: WebRTC data-channel connectivity is proven through TURN.

**Data channel: Arbitrary JSON**:

- **Problem**: Clients need to exchange arbitrary structured JSON over the data channel.
- **Acceptance**:
  - Accept input that conforms to `webrtc.schema.json`.
  - Return the corresponding JSON output only to the same client.
  - Keep data-channel state isolated between concurrent clients.
- **Outcome**: The data channel supports isolated, schema-validated, non-audio input and output.

**Sessions: Concurrent clients**:

- **Problem**: Concurrent browser clients must not receive each other's data-channel output.
- **Acceptance**:
  - Connect two browser clients concurrently.
  - Send distinct JSON values from each client.
  - Return each response only to its originating client.
- **Outcome**: Each peer connection has isolated client state and output.

**Invalid input**:

- **Problem**: Invalid data-channel messages must not be processed as valid input.
- **Acceptance**:
  - Reject malformed JSON and messages that do not conform to the input schema.
  - Keep the connection usable after rejecting an invalid message.
- **Outcome**: Invalid messages are rejected without corrupting the client session.

**Data channel: Realtime interrupt**:

- **Problem**: A client must be able to stop an in-progress data-channel response.
- **Acceptance**:
  - Start a multi-message response.
  - Interrupt that response and return an interrupted result without later chunks.
  - Keep the same data channel usable for a subsequent request.
- **Outcome**: Realtime work can be interrupted per client without disconnecting the session.

**Connection failure**:

- **Problem**: A failed or interrupted WebRTC session must not prevent other clients from working.
- **Acceptance**:
  - Handle an interrupted connection and release only its session resources.
  - Keep another client connected and usable during the failure.
  - Accept a new valid session after the failure.
- **Outcome**: Connection failure is contained to the affected client session.
