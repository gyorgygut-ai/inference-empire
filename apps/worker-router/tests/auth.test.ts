import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { verifyToken } from "../src/auth"

const fixturesDir = join(import.meta.dirname, "fixtures", "auth")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("auth", () => {
  test("valid", async () => {
    const input = json("input.json", "valid")
    const expected = json("expected.json", "valid")
    const output = await verifyToken(input.header, input.secret)
    expect(output).toBe(expected)
  })
  test("wrong-scheme", async () => {
    const input = json("input.json", "wrong-scheme")
    const expected = json("expected.json", "wrong-scheme")
    const output = await verifyToken(input.header, input.secret)
    expect(output).toBe(expected)
  })
  test("missing", async () => {
    const input = json("input.json", "missing")
    const expected = json("expected.json", "missing")
    const output = await verifyToken(input.header, input.secret)
    expect(output).toBe(expected)
  })
  test("mismatch", async () => {
    const input = json("input.json", "mismatch")
    const expected = json("expected.json", "mismatch")
    const output = await verifyToken(input.header, input.secret)
    expect(output).toBe(expected)
  })
})
