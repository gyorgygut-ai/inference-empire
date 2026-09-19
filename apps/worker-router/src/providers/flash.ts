import type { RouterInput } from "../contracts"
import type { Provider, TaskResult } from "./types"

export interface FlashCoordinates {
  baseUrl: string
}

export interface FlashSecrets {
  apiKey: string
}

function idOf(body: unknown): string {
  if (typeof body !== "object" || body === null) throw new Error("flash queue returned invalid body")
  const id: unknown = (body as Record<string, unknown>)["id"]
  if (typeof id !== "string" || id.length === 0) throw new Error("flash queue returned no id")
  return id
}

export function createFlashProvider(coords: FlashCoordinates, secrets: FlashSecrets, fetchImpl: typeof fetch = fetch): Provider {
  return {
    name: "flash",
    queue: async (input: RouterInput): Promise<string> => {
      const res = await fetchImpl(`${coords.baseUrl}/run`, {
        method: "POST",
        headers: { authorization: `Bearer ${secrets.apiKey}`, "content-type": "application/json" },
        body: JSON.stringify({ input })
      })
      if (res.status === 401) throw new Error("flash queue unauthorized")
      if (!res.ok) throw new Error(`flash queue failed: ${res.status}`)
      return idOf(await res.json())
    },
    status: async (id: string): Promise<TaskResult> => {
      const res = await fetchImpl(`${coords.baseUrl}/status/${id}`, {
        headers: { authorization: `Bearer ${secrets.apiKey}` }
      })
      if (res.status === 401) throw new Error("flash status unauthorized")
      if (!res.ok) return { status: "REJECTED" }
      const body: unknown = await res.json()
      if (typeof body !== "object" || body === null) return { status: "BUSY" }
      const rec = body as Record<string, unknown>
      if (rec["status"] === "COMPLETED") return { status: "DONE", output: rec["output"] }
      if (rec["status"] === "FAILED") return { status: "REJECTED" }
      return { status: "BUSY" }
    }
  }
}
