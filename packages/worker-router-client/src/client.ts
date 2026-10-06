export interface Config {
  baseUrl: string
  token: string
  pollIntervalMs: number
  timeoutMs: number
}

const TERMINAL = ["failed", "cancelled"]

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

async function submit(input: Record<string, unknown>, config: Config, fetchImpl: typeof fetch, signal?: AbortSignal): Promise<string> {
  const response = await fetchImpl(`${base(config)}/infer`, {
    method: "POST",
    headers: headers(config),
    body: JSON.stringify({ input }),
    signal
  })
  if (!response.ok) {
    throw await originalError(response)
  }
  const body = (await response.json()) as { task_id: string }
  return body.task_id
}

async function tick<T>(
  taskId: string,
  config: Config,
  fetchImpl: typeof fetch,
  deadline: number,
  signal?: AbortSignal
): Promise<T> {
  if (Date.now() >= deadline) {
    throw new Error(`timeout after ${config.timeoutMs}ms`)
  }
  const url = `${base(config)}/inquire?id=${encodeURIComponent(taskId)}`
  const response = await fetchImpl(url, { headers: headers(config), signal })
  if (!response.ok) {
    throw await originalError(response)
  }
  const body = (await response.json()) as { status: string; output?: unknown }
  if (body.status === "completed") {
    return body.output as T
  }
  if (TERMINAL.includes(body.status)) {
    throw new Error(body.status)
  }
  await sleep(config.pollIntervalMs, signal)
  return tick<T>(taskId, config, fetchImpl, deadline, signal)
}

export async function inferWithPolling<T>(
  input: Record<string, unknown>,
  config: Config,
  fetchImpl: typeof fetch = fetch,
  signal?: AbortSignal
): Promise<T> {
  const taskId = await submit(input, config, fetchImpl, signal)
  return tick<T>(taskId, config, fetchImpl, Date.now() + config.timeoutMs, signal)
}
