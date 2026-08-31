import type { Handler } from "../types";

// Priority 4: skip provider if we're rate limited, pick first available
export const rateLimits: Handler = (request, state) => {
  const providers = (["modal", "beam"] as const).filter(
    (p) => state.rateLimitRemaining[p] > 0,
  );
  if (!providers.length) return null;
  return providers[0];
};
