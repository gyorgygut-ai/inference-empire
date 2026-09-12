import type { Env } from "./types";
import { route } from "./handler-chain";
import { forward } from "./forward";
import { getProviderState } from "./provider-state";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const state = await getProviderState();
    const provider = route(request, state);
    return fetch(forward(request, provider!, env));
  },
} satisfies ExportedHandler<Env>;
