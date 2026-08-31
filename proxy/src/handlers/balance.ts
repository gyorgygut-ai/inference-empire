import type { Handler } from "../types";

// Priority 2: route to provider with money left
export const balance: Handler = (request, state) => {
  const providers = (["modal", "beam"] as const).filter(
    (p) => state.balance[p] > 0,
  );
  if (!providers.length) return null;
  return providers.reduce((a, b) => (state.balance[a] >= state.balance[b] ? a : b));
};
