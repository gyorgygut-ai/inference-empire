import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { encodeTaskId, decodeTaskId } from "../src/task-id"

const fixturesDir = join(import.meta.dirname, "fixtures", "task-id")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

function text(name: string, dir: string): string {
  return readFileSync(join(fixturesDir, dir, name), "utf-8").trim()
}

describe("task-id", () => {
  test("modal-roundtrip", () => {
    const input = json("input.json", "modal-roundtrip")
    const expected = text("expected.txt", "modal-roundtrip")
    const output = encodeTaskId(input.provider, input.id)
    expect(output).toBe(expected)
  })
  test("beam-roundtrip", () => {
    const input = json("input.json", "beam-roundtrip")
    const expected = text("expected.txt", "beam-roundtrip")
    const output = encodeTaskId(input.provider, input.id)
    expect(output).toBe(expected)
  })
  test("invalid-id", () => {
    const input = text("input.txt", "invalid-id")
    const expected = json("expected.json", "invalid-id")
    const output = decodeTaskId(input)
    expect(output).toBe(expected)
  })
})
