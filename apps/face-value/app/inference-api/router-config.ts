// Server-only — imported from API layer only, never from components.
// Reads dist/apps/worker-router/contract.json at build time.
import contract from "../../../../dist/apps/worker-router/contract.json"

export const routerConfig = {
  token: contract.authToken,
  baseUrl: contract.endpoints.flux2
}
