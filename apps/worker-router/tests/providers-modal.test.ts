import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { createModalProvider } from "../src/providers/modal"
import { createFetchStub, jsonResponse } from "./stubs/fetch-stub"

const fixturesDir = join(import.meta.dirname, "fixtures", "providers")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("modal provider", () => {
  test("modal-queue-id", async () => {
    const input = json("input.json", "modal-queue-id")
    const expected = json("expected.json", "modal-queue-id")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createModalProvider(input.baseUrl, fetchStub).queue(input.input)
    expect(output).toBe(expected)
  })
  test("modal-queue-request", async () => {
    const input = json("input.json", "modal-queue-request")
    const expected = json("expected.json", "modal-queue-request")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    await createModalProvider(input.baseUrl, fetchStub).queue(input.input)
    const output = { url: fetchStub.requests[0].url, method: fetchStub.requests[0].init.method }
    expect(output).toEqual(expected)
  })
  test("modal-status-done", async () => {
    const input = json("input.json", "modal-status-done")
    const expected = json("expected.json", "modal-status-done")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createModalProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("modal-status-busy", async () => {
    const input = json("input.json", "modal-status-busy")
    const expected = json("expected.json", "modal-status-busy")
    const fetchStub = createFetchStub([jsonResponse(input.response)])
    const output = await createModalProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
  test("modal-status-rejected", async () => {
    const input = json("input.json", "modal-status-rejected")
    const expected = json("expected.json", "modal-status-rejected")
    const fetchStub = createFetchStub([jsonResponse(input.response, input.responseStatus)])
    const output = await createModalProvider(input.baseUrl, fetchStub).status(input.id)
    expect(output).toEqual(expected)
  })
})
