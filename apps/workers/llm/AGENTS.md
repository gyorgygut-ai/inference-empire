# LLM Chat Completions

LLM Chat Completions worker. OpenAI-compatible Chat Completions API.

## Authentication

**Problem**: Authenticate requests without exposing Beam credentials.

**Approach**:
- Bearer token `SECRET_LLM_CHAT_COMPLETIONS_API_KEY` required for `POST /v1/chat/completions`; `project.json` maps it from `GENERATED_LLM_CHAT_COMPLETIONS_API_KEY`
- Token validated server-side

**Outcome**:
- Unauthorized requests rejected

## Contract

- History is caller-owned; the worker keeps no session state

## Acceptance Criteria

**Task**: `worker-llm:deploy-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/chat/completions` + missing or invalid token → rejects `401`
- `POST /v1/chat/completions` + malformed request body → rejects `422`
- `POST /v1/chat/completions` + authenticated messages → non-empty `choices[0].message.content`
