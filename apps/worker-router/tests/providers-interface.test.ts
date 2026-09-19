import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { createModalProvider } from "../src/providers/modal"
import { createBeamProvider } from "../src/providers/beam"
import { createFlashProvider } from "../src/providers/flash"
import { createFetchStub, jsonResponse } from "./stubs/fetch-stub"

const fixturesDir = join(import.meta.dirname, "fixtures", "providers")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("provider interface", () => {
  test("interface-modal", async () => {
    const input = json("input.json", "interface-modal")
    const expected = json("expected.json", "interface-modal")
    const provider = createModalProvider(input.baseUrl, createFetchStub([jsonResponse(input.response)]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(expected)
  })
  test("interface-beam", async () => {
    const input = json("input.json", "interface-beam")
    const expected = json("expected.json", "interface-beam")
    const provider = createBeamProvider(input.baseUrl, createFetchStub([jsonResponse(input.response)]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(expected)
  })
  test("interface-flash", async () => {
    const input = json("input.json", "interface-flash")
    const expected = json("expected.json", "interface-flash")
    const provider = createFlashProvider(input.baseUrl, createFetchStub([jsonResponse(input.response)]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(expected)
  })
})
