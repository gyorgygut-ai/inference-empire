import type { Handler } from "../types";

// Priority 1: route to provider with remaining free quota
export const freeQuota: Handler = (request, state) => {
  const providers = (["modal", "beam"] as const).filter(
    (p) => state.freeQuota[p] > 0,
  );
  if (!providers.length) return null;
  return providers.reduce((a, b) => (state.freeQuota[a] >= state.freeQuota[b] ? a : b));
};
