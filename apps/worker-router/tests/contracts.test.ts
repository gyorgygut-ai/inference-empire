import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { parseQueueBody } from "../src/contracts"

const fixturesDir = join(import.meta.dirname, "fixtures", "contracts")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("contracts", () => {
  test("flux2-valid", () => {
    const input = json("input.json", "flux2-valid")
    const expected = json("expected.json", "flux2-valid")
    const output = parseQueueBody(input, "flux2_klein9b")
    expect(output).toEqual(expected)
  })
  test("tinysd-valid", () => {
    const input = json("input.json", "tinysd-valid")
    const expected = json("expected.json", "tinysd-valid")
    const output = parseQueueBody(input, "tiny_sd")
    expect(output).toEqual(expected)
  })
  test("missing-prompt", () => {
    const input = json("input.json", "missing-prompt")
    const expected = json("expected.json", "missing-prompt")
    const output = parseQueueBody(input, "flux2_klein9b")
    expect(output).toBe(expected)
  })
  test("unknown-contract", () => {
    const input = json("input.json", "unknown-contract")
    const expected = json("expected.json", "unknown-contract")
    const output = parseQueueBody(input, "nope")
    expect(output).toBe(expected)
  })
})
