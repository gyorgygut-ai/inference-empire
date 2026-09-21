export type RealtimeStrategy = "proxy" | "relay" | "direct";

export interface ResolvedTransport {
  url: string;
  apiKey?: string;
  dangerouslyAllowAPIKeyInBrowser?: boolean;
}

export interface TransportConfig {
  /** proxy (default): same-origin /api/realtime (Next custom server in server.js).
   *  relay: ws://localhost:8080 (scripts/local_realtime_relay.py).
   *  direct: straight to wss://<REALTIME_WORKER_URL> with Bearer (dev only). */
  strategy?: RealtimeStrategy;
  /** WebSocket URL for `relay` / `direct` modes. */
  workerUrl?: string;
  /** Bearer token for `direct` mode (exposed in the browser — dev only). */
  token?: string;
}

export function resolveTransport(config: TransportConfig = {}): ResolvedTransport {
  const strategy = config.strategy ?? "proxy";

  if (strategy === "relay") {
    return { url: config.workerUrl ?? "ws://localhost:8080" };
  }

  if (strategy === "direct") {
    return {
      url: config.workerUrl ?? "",
      apiKey: config.token,
      dangerouslyAllowAPIKeyInBrowser: true,
    };
  }

  // proxy: same-origin path terminated by the Next custom server (server.js)
  return { url: "/api/realtime" };
}
