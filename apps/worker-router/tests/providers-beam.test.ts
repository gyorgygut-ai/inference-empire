import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { createBeamProvider } from "../src/providers/beam"
import { createFetchStub, jsonResponse } from "./stubs/fetch-stub"

const fixturesDir = join(import.meta.dirname, "fixtures", "providers")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("beam provider", () => {
  test("beam-queue-id", async () => {
    const input = json("input.json", "beam-queue-id")
    const expected = json("expected.json", "beam-queue-id")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createBeamProvider(input.baseUrl, fetchStub).queue(input.input)
    expect(output).toBe(expected)
  })
  test("beam-queue-request", async () => {
    const input = json("input.json", "beam-queue-request")
    const expected = json("expected.json", "beam-queue-request")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    await createBeamProvider(input.baseUrl, fetchStub).queue(input.input)
    const output = { url: fetchStub.requests[0].url, method: fetchStub.requests[0].init.method }
    expect(output).toEqual(expected)
  })
  test("beam-status-done", async () => {
    const input = json("input.json", "beam-status-done")
    const expected = json("expected.json", "beam-status-done")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createBeamProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("beam-status-busy", async () => {
    const input = json("input.json", "beam-status-busy")
    const expected = json("expected.json", "beam-status-busy")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createBeamProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("beam-status-rejected", async () => {
    const input = json("input.json", "beam-status-rejected")
    const expected = json("expected.json", "beam-status-rejected")
    const fetchStub = createFetchStub([jsonResponse(input.response, input.responseStatus)])
    const output = await createBeamProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
})
