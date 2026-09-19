import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { selectProvider } from "../src/providers/selector"

const fixturesDir = join(import.meta.dirname, "fixtures", "providers")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("selector", () => {
  test("selector-default", () => {
    const input = json("input.json", "selector-default")
    const expected = json("expected.json", "selector-default")
    const output = selectProvider(input).name
    expect(output).toBe(expected)
  })
  test("selector-pinned-beam", () => {
    const input = json("input.json", "selector-pinned-beam")
    const expected = json("expected.json", "selector-pinned-beam")
    const output = selectProvider(input.env, input.pinned).name
    expect(output).toBe(expected)
  })
  test("selector-pinned-flash", () => {
    const input = json("input.json", "selector-pinned-flash")
    const expected = json("expected.json", "selector-pinned-flash")
    const output = selectProvider(input.env, input.pinned).name
    expect(output).toBe(expected)
  })
})
