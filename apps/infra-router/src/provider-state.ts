import type { Provider, ProviderState } from "./types";

// TODO: fetch live from provider APIs
// TODO: cache at fetching layer
export async function getProviderState(): Promise<ProviderState> {
  return {
    freeQuota: { runpod: 0, beam: 0, modal: 0 },
    balance: { runpod: 0, beam: 0, modal: 0 },
    rateLimitRemaining: { runpod: 0, beam: 0, modal: 0 },
    availability: { runpod: true, beam: true, modal: true },
  };
}
