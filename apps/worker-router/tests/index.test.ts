import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { SELF } from "cloudflare:test"

const fixturesDir = join(import.meta.dirname, "fixtures", "index")

function json(name: string, dir: string): any {
  return JSON.parse(readFileSync(join(fixturesDir, dir, name), "utf-8"))
}

describe("index", () => {
  test("queue-202", async () => {
    const input = json("input.json", "queue-202")
    const expected = json("expected.json", "queue-202")
    const headers: Record<string, string> = { "content-type": "application/json" }
    if (input.auth !== null) headers["authorization"] = input.auth
    const res = await SELF.fetch(`https://router${input.path}`, { method: input.method, headers, body: JSON.stringify(input.body) })
    expect(res.status).toBe(expected.status)
  })
  test("queue-400", async () => {
    const input = json("input.json", "queue-400")
    const expected = json("expected.json", "queue-400")
    const headers: Record<string, string> = { "content-type": "application/json" }
    if (input.auth !== null) headers["authorization"] = input.auth
    const res = await SELF.fetch(`https://router${input.path}`, { method: input.method, headers, body: JSON.stringify(input.body) })
    expect(res.status).toBe(expected.status)
  })
  test("task-bad-id", async () => {
    const input = json("input.json", "task-bad-id")
    const expected = json("expected.json", "task-bad-id")
    const headers: Record<string, string> = {}
    if (input.auth !== null) headers["authorization"] = input.auth
    const res = await SELF.fetch(`https://router${input.path}`, { headers })
    expect(res.status).toBe(expected.status)
  })
  test("unauthorized", async () => {
    const input = json("input.json", "unauthorized")
    const expected = json("expected.json", "unauthorized")
    const res = await SELF.fetch(`https://router${input.path}`, { method: input.method })
    expect(res.status).toBe(expected.status)
  })
  test("unknown-route", async () => {
    const input = json("input.json", "unknown-route")
    const expected = json("expected.json", "unknown-route")
    const headers: Record<string, string> = {}
    if (input.auth !== null) headers["authorization"] = input.auth
    const res = await SELF.fetch(`https://router${input.path}`, { headers })
    expect(res.status).toBe(expected.status)
  })
})
