import type { RouterInput } from "../contracts"
import type { Provider, TaskResult } from "./types"

export interface BeamCoordinates {
  invokeUrl: string
  taskApi: string
}

export interface BeamSecrets {
  basicToken: string
  bearerToken: string
}

function taskIdOf(body: unknown): string {
  if (typeof body !== "object" || body === null) throw new Error("beam queue returned invalid body")
  const id: unknown = (body as Record<string, unknown>)["task_id"]
  if (typeof id !== "string" || id.length === 0) throw new Error("beam queue returned no task_id")
  return id
}

export function createBeamProvider(coords: BeamCoordinates, secrets: BeamSecrets, fetchImpl: typeof fetch = fetch): Provider {
  return {
    name: "beam",
    queue: async (input: RouterInput): Promise<string> => {
      const res = await fetchImpl(coords.invokeUrl, {
        method: "POST",
        headers: { authorization: `Basic ${secrets.basicToken}`, "content-type": "application/json" },
        body: JSON.stringify(input)
      })
      if (res.status === 401) throw new Error("beam queue unauthorized")
      if (!res.ok) throw new Error(`beam queue failed: ${res.status}`)
      return taskIdOf(await res.json())
    },
    status: async (id: string): Promise<TaskResult> => {
      const res = await fetchImpl(`${coords.taskApi}/v2/task/${id}/`, {
        headers: { authorization: `Bearer ${secrets.bearerToken}` }
      })
      if (res.status === 401) throw new Error("beam status unauthorized")
      if (!res.ok) return { status: "REJECTED" }
      const body: unknown = await res.json()
      if (typeof body !== "object" || body === null) return { status: "BUSY" }
      const rec = body as Record<string, unknown>
      if (rec["status"] === "COMPLETE") return { status: "DONE", output: rec["outputs"] }
      if (rec["status"] === "FAILED") return { status: "REJECTED" }
      return { status: "BUSY" }
    }
  }
}
