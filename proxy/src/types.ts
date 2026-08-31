export type Provider = "runpod" | "beam" | "modal";

export interface Env {
  RUNPOD_API_KEY: string;
  BEAM_API_KEY: string;
  MODAL_API_KEY: string;
  RUNPOD_ENDPOINT: string;
  BEAM_ENDPOINT: string;
  MODAL_ENDPOINT: string;
}

export interface ProviderState {
  freeQuota: Record<Provider, number>;
  balance: Record<Provider, number>;
  rateLimitRemaining: Record<Provider, number>;
  availability: Record<Provider, boolean>;
}

export type Handler = (
  request: Request,
  state: ProviderState,
) => Provider | null;
