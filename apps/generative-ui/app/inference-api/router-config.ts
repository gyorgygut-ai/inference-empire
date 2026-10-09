let configCache: { baseUrl: string; authToken: string }

function loadConfig(): { baseUrl: string; authToken: string } {
  if (configCache) { return configCache }
  const baseUrl = process.env.FLUX2_ROUTER_URL || ""
  if (!baseUrl) { throw new Error("missing FLUX2_ROUTER_URL env var") }
  const authToken = process.env.FLUX2_ROUTER_TOKEN || ""
  if (!authToken) { throw new Error("missing FLUX2_ROUTER_TOKEN env var") }
  configCache = { baseUrl, authToken }
  return configCache
}

export const workerRouterConfig = {
  get baseUrl(): string { return loadConfig().baseUrl },
  get authToken(): string { return loadConfig().authToken },
}
