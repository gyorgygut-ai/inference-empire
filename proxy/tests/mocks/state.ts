import type { Provider, ProviderState } from "../../src/types";

interface ProviderConfig {
  freeQuota?: number;
  balance?: number;
  rateLimitRemaining?: number;
  available?: boolean;
}

interface StateConfig {
  runpod?: ProviderConfig;
  modal?: ProviderConfig;
  beam?: ProviderConfig;
}

const defaults: ProviderConfig = {
  freeQuota: 0,
  balance: 0,
  rateLimitRemaining: 100,
  available: true,
};

export function buildState(config: StateConfig): ProviderState {
  const merge = (c?: ProviderConfig) => ({ ...defaults, ...c });
  const runpod = merge(config.runpod);
  const modal = merge(config.modal);
  const beam = merge(config.beam);

  return {
    freeQuota: { runpod: runpod.freeQuota!, modal: modal.freeQuota!, beam: beam.freeQuota! },
    balance: { runpod: runpod.balance!, modal: modal.balance!, beam: beam.balance! },
    rateLimitRemaining: { runpod: runpod.rateLimitRemaining!, modal: modal.rateLimitRemaining!, beam: beam.rateLimitRemaining! },
    availability: { runpod: runpod.available!, modal: modal.available!, beam: beam.available! },
  };
}
