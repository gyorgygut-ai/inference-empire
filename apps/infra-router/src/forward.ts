import type { Env, Provider } from "./types";

const ENDPOINTS: Record<Provider, string> = {
  runpod: "RUNPOD_ENDPOINT",
  beam: "BEAM_ENDPOINT",
  modal: "MODAL_ENDPOINT",
};

export function forward(request: Request, provider: Provider, env: Env): Request {
  const endpoint = env[ENDPOINTS[provider]];
  const url = new URL(request.url);
  const target = new URL(endpoint);
  url.hostname = target.hostname;
  url.port = target.port;
  url.protocol = target.protocol;
  return new Request(url.toString(), request);
}
