import { describe, test, expect, vi, afterEach } from "vitest"
import { SELF } from "cloudflare:test"
import { createFetchStub } from "./stubs/fetch-stub"
import queue202Input from "./fixtures/index/queue-202/input.json"
import queue202Expected from "./fixtures/index/queue-202/expected.json"
import queue400Input from "./fixtures/index/queue-400/input.json"
import queue400Expected from "./fixtures/index/queue-400/expected.json"
import badIdInput from "./fixtures/index/task-bad-id/input.json"
import badIdExpected from "./fixtures/index/task-bad-id/expected.json"
import unauthorizedInput from "./fixtures/index/unauthorized/input.json"
import unauthorizedExpected from "./fixtures/index/unauthorized/expected.json"
import unknownInput from "./fixtures/index/unknown-route/input.json"
import unknownExpected from "./fixtures/index/unknown-route/expected.json"
import taskDoneInput from "./fixtures/index/task-done/input.json"
import taskDoneExpected from "./fixtures/index/task-done/expected.json"

function headersFor(auth: string | null, json: boolean): Record<string, string> {
  const headers: Record<string, string> = {}
  if (json) headers["content-type"] = "application/json"
  if (auth !== null) headers["authorization"] = auth
  return headers
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("index", () => {
  test("queue-202", async () => {
    vi.stubGlobal("fetch", createFetchStub([{ body: taskDoneInput.queueResponse }]))
    const res = await SELF.fetch(`https://router${queue202Input.path}`, {
      method: queue202Input.method,
      headers: headersFor(queue202Input.auth, true),
      body: JSON.stringify(queue202Input.body)
    })
    expect(res.status).toBe(queue202Expected.status)
  })
  test("queue-400", async () => {
    const res = await SELF.fetch(`https://router${queue400Input.path}`, {
      method: queue400Input.method,
      headers: headersFor(queue400Input.auth, true),
      body: JSON.stringify(queue400Input.body)
    })
    expect(res.status).toBe(queue400Expected.status)
  })
  test("task-bad-id", async () => {
    const res = await SELF.fetch(`https://router${badIdInput.path}`, { headers: headersFor(badIdInput.auth, false) })
    expect(res.status).toBe(badIdExpected.status)
  })
  test("unauthorized", async () => {
    const res = await SELF.fetch(`https://router${unauthorizedInput.path}`, { method: unauthorizedInput.method })
    expect(res.status).toBe(unauthorizedExpected.status)
  })
  test("unknown-route", async () => {
    const res = await SELF.fetch(`https://router${unknownInput.path}`, { headers: headersFor(unknownInput.auth, false) })
    expect(res.status).toBe(unknownExpected.status)
  })
  test("task-done", async () => {
    vi.stubGlobal("fetch", createFetchStub([{ body: taskDoneInput.queueResponse }, { body: taskDoneInput.statusResponse }]))
    const queued = await SELF.fetch(`https://router${taskDoneInput.path}`, {
      method: taskDoneInput.method,
      headers: headersFor(taskDoneInput.auth, true),
      body: JSON.stringify(taskDoneInput.body)
    })
    const queuedBody: unknown = await queued.json()
    const taskId: string = (queuedBody as Record<string, string>)["task_id"]
    const res = await SELF.fetch(`https://router/task/${taskId}`, { headers: headersFor(taskDoneInput.auth, false) })
    expect(await res.json()).toEqual(taskDoneExpected)
  })
})
