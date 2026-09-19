import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { createFlashProvider } from "../src/providers/flash"
import { createFetchStub, jsonResponse } from "./stubs/fetch-stub"

const fixturesDir = join(import.meta.dirname, "fixtures", "providers")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("flash provider", () => {
  test("flash-queue-id", async () => {
    const input = json("input.json", "flash-queue-id")
    const expected = json("expected.json", "flash-queue-id")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createFlashProvider(input.baseUrl, fetchStub).queue(input.input)
    expect(output).toBe(expected)
  })
  test("flash-queue-request", async () => {
    const input = json("input.json", "flash-queue-request")
    const expected = json("expected.json", "flash-queue-request")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    await createFlashProvider(input.baseUrl, fetchStub).queue(input.input)
    const output = { url: fetchStub.requests[0].url, method: fetchStub.requests[0].init.method }
    expect(output).toEqual(expected)
  })
  test("flash-status-done", async () => {
    const input = json("input.json", "flash-status-done")
    const expected = json("expected.json", "flash-status-done")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createFlashProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("flash-status-busy", async () => {
    const input = json("input.json", "flash-status-busy")
    const expected = json("expected.json", "flash-status-busy")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createFlashProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("flash-status-rejected", async () => {
    const input = json("input.json", "flash-status-rejected")
    const expected = json("expected.json", "flash-status-rejected")
    const fetchStub = createFetchStub([jsonResponse(input.response, input.responseStatus)])
    const output = await createFlashProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
})
