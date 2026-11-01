

# LLM Chat Completions

LLM Chat Completions worker. OpenAI-compatible Chat Completions API.

## SPECS

## Hugging Face authentication

Authenticate every Hugging Face Hub request with `SECRET_HUGGINGFACE_TOKEN`. Pass the token directly to Hub APIs and initialize Hub authentication before libraries perform internal downloads.

**Authentication**:

- **Problem**: Requests need authentication without exposing Beam credentials.
- **Acceptance**:
  - Require Bearer token `SECRET_LLM_CHAT_COMPLETIONS_API_KEY` on `POST /v1/chat/completions`.
  - Map it in `project.json` from `GENERATED_LLM_CHAT_COMPLETIONS_API_KEY`.
  - Validate the token server-side.
  - Reject missing or invalid tokens with `401`.
- **Outcome**: Only callers with the configured API key can request completions.

**Request and response**:

- **Problem**: Callers need chat completions without the worker retaining their conversation state.
- **Acceptance**:
  - Keep conversation history caller-owned; the worker stores no session state.
  - Reject malformed request bodies with `422`.
  - For authenticated messages, return non-empty `choices[0].message.content`.
- **Outcome**: Conversation state stays with the caller; the worker returns the completion.

**Health**:

- **Problem**: Deployment health checks must not trigger inference.
- **Acceptance**:
  - `GET /health` succeeds without triggering inference.
- **Outcome**: Health checks do not run inference.

## DEPLOY

**Task**: `worker-llm:deploy-beam`
apps/workers/voice/AGENTS.md
