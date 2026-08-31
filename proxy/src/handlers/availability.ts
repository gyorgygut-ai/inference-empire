import type { Handler } from "../types";

// Priority 5: skip provider if it's slow or unresponsive
export const availability: Handler = (request, state) => {
  const providers = (["modal", "beam"] as const).filter(
    (p) => state.availability[p],
  );
  if (!providers.length) return null;
  return providers[0];
};
