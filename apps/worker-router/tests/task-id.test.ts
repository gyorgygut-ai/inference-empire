import { describe, test, expect } from "vitest"
import { encodeTaskId, decodeTaskId, type ProviderName } from "../src/task-id"
import modalInput from "./fixtures/task-id/modal-roundtrip/input.json"
import modalExpected from "./fixtures/task-id/modal-roundtrip/expected.txt?raw"
import beamInput from "./fixtures/task-id/beam-roundtrip/input.json"
import beamExpected from "./fixtures/task-id/beam-roundtrip/expected.txt?raw"
import invalidInput from "./fixtures/task-id/invalid-id/input.txt?raw"
import invalidExpected from "./fixtures/task-id/invalid-id/expected.json"

describe("task-id", () => {
  test("modal-roundtrip", () => {
    const output = encodeTaskId(modalInput.provider as ProviderName, modalInput.id)
    expect(output).toBe(modalExpected.trim())
  })
  test("beam-roundtrip", () => {
    const output = encodeTaskId(beamInput.provider as ProviderName, beamInput.id)
    expect(output).toBe(beamExpected.trim())
  })
  test("invalid-id", () => {
    const output = decodeTaskId(invalidInput.trim())
    expect(output).toBe(invalidExpected)
  })
})
