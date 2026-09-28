import type { Flux2Klein9BInput, Flux2Klein9BOutput } from "./schema"

export type { Flux2Klein9BInput, Flux2Klein9BOutput }
export type RequestPayload = Flux2Klein9BInput
export type ResponsePayload = Flux2Klein9BOutput

export interface InferenceConfig {
  baseUrl: string
  token: string
  maxPollMillis: number
  pollIntervalMillis: number
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export async function postQueue(input: RequestPayload, config: InferenceConfig, fetchImpl: typeof fetch = fetch): Promise<string> {
  const res = await fetchImpl(`${config.baseUrl}/queue`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ input })
  })
  if (!res.ok) {
    throw new Error(`QUEUE_HTTP_${res.status}`)
  }
  const body = await res.json()
  return (body as { task_id: string }).task_id
}

async function getStatus(taskId: string, config: InferenceConfig, fetchImpl: typeof fetch = fetch): Promise<{ status: string; output?: Flux2Klein9BOutput }> {
  const res = await fetchImpl(`${config.baseUrl}/task/${taskId}`, {
    headers: { Authorization: `Bearer ${config.token}` }
  })
  if (!res.ok) {
    throw new Error(`QUEUE_HTTP_${res.status}`)
  }
  return (await res.json()) as { status: string; output?: Flux2Klein9BOutput }
}

export async function pollQueue(taskId: string, config: InferenceConfig, fetchImpl: typeof fetch = fetch): Promise<{ output: Flux2Klein9BOutput }> {
  const start = Date.now()
  while (Date.now() - start < config.maxPollMillis) {
    const result = await getStatus(taskId, config, fetchImpl)
    if (result.status === "DONE") {
      return { output: result.output as Flux2Klein9BOutput }
    }
    if (result.status === "REJECTED") {
      throw new Error("REJECTED")
    }
    await sleep(config.pollIntervalMillis)
  }
  throw new Error("SERVER_TIMEOUT")
}
