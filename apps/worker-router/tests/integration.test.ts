import { describe, test, expect, vi, afterEach } from "vitest"
import { SELF } from "cloudflare:test"
import { createFetchStub } from "./stubs/fetch-stub"
import { decodeTaskId } from "../src/task-id"

function headersFor(auth: string | null, json: boolean): Record<string, string> {
  const headers: Record<string, string> = {}
  if (json) headers["content-type"] = "application/json"
  if (auth !== null) headers["authorization"] = auth
  return headers
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("integration", () => {
  test("queue → task → result", async () => {
    const queueResponse = { call_id: "m-1" }
    const statusResponse = { artifact: { presigned_url: "https://r2/t.png" } }
    vi.stubGlobal("fetch", createFetchStub([
      { body: queueResponse },
      { body: statusResponse },
    ]))

    const queued = await SELF.fetch("https://router/queue", {
      method: "POST",
      headers: headersFor("Bearer secret", true),
      body: JSON.stringify({ input: { prompt: "a red square" } }),
    })
    expect(queued.status).toBe(202)

    const body: { task_id: string } = await queued.json()
    const taskId = body.task_id

    const decoded = decodeTaskId(taskId)
    expect(decoded).not.toBeNull()
    expect(decoded!.provider).toBe("modal")
    expect(decoded!.id).toBe("m-1")

    const res = await SELF.fetch(`https://router/task/${taskId}`, {
      headers: headersFor("Bearer secret", false),
    })
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ status: "DONE", output: { artifact: { presigned_url: "https://r2/t.png" } } })
  })
})
