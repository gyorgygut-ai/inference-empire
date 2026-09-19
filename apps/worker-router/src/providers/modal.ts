import type { RouterInput } from "../contracts"
import type { Provider, TaskResult } from "./types"

export interface ModalCoordinates {
  baseUrl: string
}

export interface ModalSecrets {
  wrapperToken: string
}

function callIdOf(body: unknown): string {
  if (typeof body !== "object" || body === null) throw new Error("modal queue returned invalid body")
  const id: unknown = (body as Record<string, unknown>)["call_id"]
  if (typeof id !== "string" || id.length === 0) throw new Error("modal queue returned no call_id")
  return id
}

export function createModalProvider(coords: ModalCoordinates, secrets: ModalSecrets, fetchImpl: typeof fetch = fetch): Provider {
  return {
    name: "modal",
    queue: async (input: RouterInput): Promise<string> => {
      const res = await fetchImpl(`${coords.baseUrl}/submit`, {
        method: "POST",
        headers: { authorization: `Bearer ${secrets.wrapperToken}`, "content-type": "application/json" },
        body: JSON.stringify({ input })
      })
      if (res.status === 401) throw new Error("modal queue unauthorized")
      if (!res.ok) throw new Error(`modal queue failed: ${res.status}`)
      return callIdOf(await res.json())
    },
    status: async (id: string): Promise<TaskResult> => {
      const res = await fetchImpl(`${coords.baseUrl}/result/${id}`, {
        headers: { authorization: `Bearer ${secrets.wrapperToken}` }
      })
      if (res.status === 401) throw new Error("modal status unauthorized")
      if (res.status === 202) return { status: "BUSY" }
      if (res.status === 404) return { status: "REJECTED" }
      if (!res.ok) return { status: "REJECTED" }
      return { status: "DONE", output: await res.json() }
    }
  }
}
