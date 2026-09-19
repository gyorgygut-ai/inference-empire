import { describe, test, expect } from "vitest"
import { selectProvider } from "../src/providers/selector"
import type { ProviderName } from "../src/task-id"
import defaultInput from "./fixtures/providers/selector-default/input.json"
import defaultExpected from "./fixtures/providers/selector-default/expected.json"
import beamInput from "./fixtures/providers/selector-pinned-beam/input.json"
import beamExpected from "./fixtures/providers/selector-pinned-beam/expected.json"
import flashInput from "./fixtures/providers/selector-pinned-flash/input.json"
import flashExpected from "./fixtures/providers/selector-pinned-flash/expected.json"
import unconfiguredInput from "./fixtures/providers/selector-unconfigured-beam/input.json"
import unconfiguredExpected from "./fixtures/providers/selector-unconfigured-beam/expected.json"

describe("selector", () => {
  test("selector-default", () => {
    const output = selectProvider(defaultInput.coords, defaultInput.secrets).name
    expect(output).toBe(defaultExpected)
  })
  test("selector-pinned-beam", () => {
    const output = selectProvider(beamInput.coords, beamInput.secrets, beamInput.pinned as ProviderName).name
    expect(output).toBe(beamExpected)
  })
  test("selector-pinned-flash", () => {
    const output = selectProvider(flashInput.coords, flashInput.secrets, flashInput.pinned as ProviderName).name
    expect(output).toBe(flashExpected)
  })
  test("selector-unconfigured-beam", () => {
    expect(() => selectProvider(unconfiguredInput.coords, unconfiguredInput.secrets, unconfiguredInput.pinned as ProviderName)).toThrow(unconfiguredExpected)
  })
})
