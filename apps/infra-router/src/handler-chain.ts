import type { Handler, Provider, ProviderState } from "./types";
import { freeQuota } from "./handlers/free-quota";
import { balance } from "./handlers/balance";
import { modelMatch } from "./handlers/model-match";
import { rateLimits } from "./handlers/rate-limits";
import { availability } from "./handlers/availability";
import { fallback } from "./handlers/fallback";

const handlers: Handler[] = [
  freeQuota,
  balance,
  modelMatch,
  rateLimits,
  availability,
  fallback,
];

export function route(request: Request, state: ProviderState): Provider | null {
  for (const handler of handlers) {
    const result = handler(request, state);
    if (result) return result;
  }

  return null;
}
