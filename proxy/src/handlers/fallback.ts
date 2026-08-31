import type { Handler } from "../types";

// Priority 6: last resort — pick first available provider
export const fallback: Handler = (request, state) => {
  const providers = ["beam", "modal"] as const;
  for (const p of providers) {
    if (state.availability[p] && state.balance[p] > 0) return p;
  }
  return providers[0];
};
