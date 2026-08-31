# Inference Router Proxy

Cloudflare Worker that routes inference requests to Runpod, Beam, or Modal.

- Chain of responsibility — one handler per file in `handlers/`
- Handlers check provider state, first to claim picks the provider
- ProviderState fetches live balances/quotas, cached at the fetching layer

## Handler Priority Chain

1. Free Quota
2. Balance
3. Model/GPU Match
4. Rate Limits
5. Availability

## Provider Interaction

- **Runpod**: Python SDK (`runpod`) wraps GraphQL but has no balance method. Custom `myself` GraphQL query returns `clientBalance`, `machineQuota`, `spendLimit`. Auth: `Authorization: Bearer <token>`
- **Modal**: Python SDK — `Workspace.billing.summary()` returns `metered_cost`, `billed_cost`. CLI: `modal billing summary`. No REST API. Auth: `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`
- **Beam**: Go/Python/JS SDKs exist but none expose billing. No API to query credits — balance only returned in gRPC error responses (`required_cents`, `available_cents`) when compute launch fails. Dashboard: `platform.beam.cloud/settings/credits`. Auth: Bearer token
