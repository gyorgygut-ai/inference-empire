import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { infer, poll } from "./client"
import type { Config } from "./client"

const fixturesDir = join(import.meta.dirname, "fixtures")

function fixture<T>(dir: string, name: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8")) as T
}

interface QueuedResponse {
  status: number
  body: unknown
}

interface Input {
  baseUrl: string
  token: string
  prompt?: string
  taskId?: string
  pollIntervalMs: number
  timeoutMs: number
  responses: QueuedResponse[]
}

interface ExpectedResult {
  output: unknown
  requests: string[]
}

interface ExpectedError {
  error: string
  requests?: string[]
}

class QueuedFetch {
  private seen: string[] = []

  constructor(private queue: QueuedResponse[]) {}

  fetch: typeof fetch = async (input) => {
    this.seen.push(String(input))

    const next = this.queue.shift()
    if (!next) {
      throw new Error("QueuedFetch exhausted")
    }

    return new Response(JSON.stringify(next.body), { status: next.status })
  }

  requests(): string[] {
    return this.seen
  }
}

function config(input: Input): Config {
  return {
    baseUrl: input.baseUrl,
    token: input.token,
    pollIntervalMs: input.pollIntervalMs,
    timeoutMs: input.timeoutMs
  }
}

describe("infer", () => {
  test("infer-completes", async () => {
    // setup
    const input = fixture<Input>("infer-completes", "input.json")
    const expected = fixture<ExpectedResult>("infer-completes", "expected.json")
    const stub = new QueuedFetch(input.responses)

    // act
    const output = await infer<unknown>(input.prompt!, config(input), stub.fetch)

    // assert
    expect(output).toEqual(expected.output)
    expect(stub.requests()).toEqual(expected.requests)
  })

  test("infer-failed", async () => {
    // setup
    const input = fixture<Input>("infer-failed", "input.json")
    const expected = fixture<ExpectedError>("infer-failed", "expected.json")
    const stub = new QueuedFetch(input.responses)

    // act
    const act = infer<unknown>(input.prompt!, config(input), stub.fetch)

    // assert
    await expect(act).rejects.toThrow(expected.error)
    expect(stub.requests()).toEqual(expected.requests)
  })

  test("infer-timeout", async () => {
    // setup
    const input = fixture<Input>("infer-timeout", "input.json")
    const expected = fixture<ExpectedError>("infer-timeout", "expected.json")
    const stub = new QueuedFetch(input.responses)

    // act
    const act = infer<unknown>(input.prompt!, config(input), stub.fetch)

    // assert
    await expect(act).rejects.toThrow(expected.error)
  })

  test("unauthorized", async () => {
    // setup
    const input = fixture<Input>("unauthorized", "input.json")
    const expected = fixture<ExpectedError>("unauthorized", "expected.json")
    const stub = new QueuedFetch(input.responses)

    // act
    const act = infer<unknown>(input.prompt!, config(input), stub.fetch)

    // assert
    await expect(act).rejects.toThrow(expected.error)
    expect(stub.requests()).toEqual(expected.requests)
  })
})

describe("poll", () => {
  test("poll-resume", async () => {
    // setup
    const input = fixture<Input>("poll-resume", "input.json")
    const expected = fixture<ExpectedResult>("poll-resume", "expected.json")
    const stub = new QueuedFetch(input.responses)

    // act
    const output = await poll<unknown>(input.taskId!, config(input), stub.fetch)

    // assert
    expect(output).toEqual(expected.output)
    expect(stub.requests()).toEqual(expected.requests)
  })
})
