export interface Config {
  baseUrl: string
  token: string
  pollIntervalMs: number
  timeoutMs: number
}

export type TaskStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED"

export interface InferResponse {
  task_id: string
}

export interface InquireResponse<Output> {
  status: TaskStatus
  output?: Output
}

const TERMINAL: TaskStatus[] = ["FAILED", "CANCELLED"]

function base(config: Config): string {
  return config.baseUrl.replace(/\/+$/, "")
}

function headers(config: Config): Record<string, string> {
  return { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json" }
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(), ms)
    if (signal) {
      signal.addEventListener("abort", () => {
        clearTimeout(timer)
        reject(new Error("aborted"))
      }, { once: true })
    }
  })
}

async function originalError(response: Response): Promise<Error> {
  const text = await response.text()
  try {
    const body = JSON.parse(text) as { error?: string }
    return new Error(body.error ?? text)
  } catch {
    return new Error(text)
  }
}

async function submit<Input extends Record<string, unknown>>(input: Input, config: Config, fetchImpl: typeof fetch, signal?: AbortSignal): Promise<string> {
  const response = await fetchImpl(`${base(config)}/q`, {
    method: "POST",
    headers: headers(config),
    body: JSON.stringify({ input }),
    signal
  })
  if (!response.ok) {
    throw await originalError(response)
  }
  const body = (await response.json()) as InferResponse
  return body.task_id
}

async function tick<Output>(
  taskId: string,
  config: Config,
  fetchImpl: typeof fetch,
  deadline: number,
  signal?: AbortSignal
): Promise<Output> {
  if (Date.now() >= deadline) {
    throw new Error(`timeout after ${config.timeoutMs}ms`)
  }
  const url = `${base(config)}/sup?id=${encodeURIComponent(taskId)}`
  const response = await fetchImpl(url, { headers: headers(config), signal })
  if (!response.ok) {
    throw await originalError(response)
  }
  const body = (await response.json()) as InquireResponse<Output>
  if (body.status === "COMPLETED") {
    return body.output as Output
  }
  if (TERMINAL.includes(body.status)) {
    throw new Error(body.status)
  }
  await sleep(config.pollIntervalMs, signal)
  return tick<Output>(taskId, config, fetchImpl, deadline, signal)
}

export async function inferWithPolling<Input extends Record<string, unknown>, Output>(
  input: Input,
  config: Config,
  fetchImpl: typeof fetch = fetch,
  signal?: AbortSignal
): Promise<Output> {
  const taskId = await submit(input, config, fetchImpl, signal)
  return tick<Output>(taskId, config, fetchImpl, Date.now() + config.timeoutMs, signal)
}
