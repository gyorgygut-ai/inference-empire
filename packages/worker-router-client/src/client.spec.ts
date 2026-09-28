import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { inferWithPolling } from "./client"
import type { Config } from "./client"

const fixturesDir = join(import.meta.dirname, "fixtures")

function fixture<T>(dir: string, name: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8")) as T
}

type Prebaked =
  | { status: number; body: unknown }
  | { reject: string }

interface Input {
  baseUrl: string
  token: string
  prompt: string
  pollIntervalMs: number
  timeoutMs: number
  responses: Prebaked[]
}

interface ExpectedResult {
  output: unknown
  requests: string[]
}

interface ExpectedError {
  error: string
  requests: string[]
}

class PrebakedFetch {
  private seen: string[] = []

  constructor(private queue: Prebaked[]) {}

  fetch: typeof fetch = async (input) => {
    this.seen.push(String(input))

    const next = this.queue.shift()
    if (!next) {
      throw new Error("PrebakedFetch exhausted")
    }

    if ("reject" in next) {
      throw new Error(next.reject)
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

describe("inferWithPolling", () => {
  test("rejects-immediately", async () => {
    // setup
    const input = fixture<Input>("rejects-immediately", "input.json")
    const expected = fixture<ExpectedError>("rejects-immediately", "expected.json")
    const fetcher = new PrebakedFetch(input.responses)

    // act
    const act = inferWithPolling<unknown>(input.prompt, config(input), fetcher.fetch)

    // assert
    await expect(act).rejects.toThrow(expected.error)
    expect(fetcher.requests()).toEqual(expected.requests)
  })

  test("completes-immediately", async () => {
    // setup
    const input = fixture<Input>("completes-immediately", "input.json")
    const expected = fixture<ExpectedResult>("completes-immediately", "expected.json")
    const fetcher = new PrebakedFetch(input.responses)

    // act
    const output = await inferWithPolling<unknown>(input.prompt, config(input), fetcher.fetch)

    // assert
    expect(output).toEqual(expected.output)
    expect(fetcher.requests()).toEqual(expected.requests)
  })

  test("completes-on-fifth-invocation", async () => {
    // setup
    const input = fixture<Input>("completes-on-fifth-invocation", "input.json")
    const expected = fixture<ExpectedResult>("completes-on-fifth-invocation", "expected.json")
    const fetcher = new PrebakedFetch(input.responses)

    // act
    const output = await inferWithPolling<unknown>(input.prompt, config(input), fetcher.fetch)

    // assert
    expect(output).toEqual(expected.output)
    expect(fetcher.requests()).toEqual(expected.requests)
  })
})
