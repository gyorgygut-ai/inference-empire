import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { postQueue, pollQueue, pingRouter } from "../api"
import { createFetchStub } from "./stubs/fetch-stub"

const fixturesDir = join(import.meta.dirname, "fixtures")

function readInput<T>(path: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, path), "utf-8"))
}

function readExpected<T>(path: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, path), "utf-8"))
}

describe("postQueue", () => {
  test("queue/202-success", async () => {
    const input = readInput<{ input: unknown; config: object }>("queue/202-success/input.json")
    const expected = readExpected<{ task_id: string }>("queue/202-success/expected.json")
    const stub = createFetchStub([{ body: { task_id: expected.task_id }, status: 202 }])
    const result = await postQueue(input.input as never, input.config as never, stub)
    expect(result).toBe(expected.task_id)
  })
})

describe("pollQueue", () => {
  test("poll/complete", async () => {
    const input = readInput<{ taskId: string; config: object }>("poll/complete/input.json")
    const expected = readExpected<{ output: unknown }>("poll/complete/expected.json")
    const responses = readExpected<Array<{ body?: unknown; status?: number }>>("poll/complete/stubs/responses.json")
    const stub = createFetchStub(responses)
    const result = await pollQueue(input.taskId, input.config as never, stub)
    expect(result).toEqual(expected)
  })

  test("poll/rejected", async () => {
    const input = readInput<{ taskId: string; config: object }>("poll/rejected/input.json")
    const expected = readExpected<{ error: string }>("poll/rejected/expected.json")
    const responses = readExpected<Array<{ body?: unknown; status?: number }>>("poll/rejected/stubs/responses.json")
    const stub = createFetchStub(responses)
    let thrown = false
    try {
      await pollQueue(input.taskId, input.config as never, stub)
    } catch (e) {
      thrown = true
      expect((e as Error).message).toBe(expected.error)
    }
    expect(thrown).toBe(true)
  })

  test("poll/timeout", async () => {
    const input = readInput<{ taskId: string; config: object }>("poll/timeout/input.json")
    const expected = readExpected<{ error: string }>("poll/timeout/expected.json")
    const responses = readExpected<Array<{ body?: unknown; status?: number }>>("poll/timeout/stubs/responses.json")
    const stub = createFetchStub(responses)
    let thrown = false
    try {
      await pollQueue(input.taskId, input.config as never, stub)
    } catch (e) {
      thrown = true
      expect((e as Error).message).toBe(expected.error)
    }
    expect(thrown).toBe(true)
  })
})

describe("pingRouter", () => {
  test("ping/reachable", async () => {
    const input = readInput<{ config: object }>("ping/reachable/input.json")
    const expected = readExpected<boolean>("ping/reachable/expected.json")
    const responses = readExpected<Array<{ body?: unknown; status?: number }>>("ping/reachable/stubs/responses.json")
    const stub = createFetchStub(responses)
    const result = await pingRouter(input.config as never, stub)
    expect(result).toBe(expected)
  })

  test("ping/unreachable", async () => {
    const input = readInput<{ config: object }>("ping/unreachable/input.json")
    const expected = readExpected<boolean>("ping/unreachable/expected.json")
    const responses = readExpected<Array<{ body?: unknown; status?: number }>>("ping/unreachable/stubs/responses.json")
    const stub = createFetchStub(responses)
    const result = await pingRouter(input.config as never, stub)
    expect(result).toBe(expected)
  })
})
