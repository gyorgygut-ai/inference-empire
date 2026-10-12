# task-queue-client

- Client for task-queue API: `POST /q`, `GET /sup`
- One call in, result out — submit and poll encapsulated
- Config is value bag only: base URL, token, poll interval, timeout
- Dependencies are separate args: `fetchImpl` plus optional `AbortSignal`
- Polls until terminal or timeout — terminal values `COMPLETED | FAILED | CANCELLED`
- Task IDs opaque — pass back, never decode
- No env reads, no module state, no singleton
