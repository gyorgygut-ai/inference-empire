import { describe, test, expect } from "vitest"
import { parseQueueBody } from "../src/contracts"
import flux2Input from "./fixtures/contracts/flux2-valid/input.json"
import flux2Expected from "./fixtures/contracts/flux2-valid/expected.json"
import tinysdInput from "./fixtures/contracts/tinysd-valid/input.json"
import tinysdExpected from "./fixtures/contracts/tinysd-valid/expected.json"
import missingInput from "./fixtures/contracts/missing-prompt/input.json"
import missingExpected from "./fixtures/contracts/missing-prompt/expected.json"
import unknownInput from "./fixtures/contracts/unknown-contract/input.json"
import unknownExpected from "./fixtures/contracts/unknown-contract/expected.json"

describe("contracts", () => {
  test("flux2-valid", () => {
    const output = parseQueueBody(flux2Input, "flux2_klein9b")
    expect(output).toEqual(flux2Expected)
  })
  test("tinysd-valid", () => {
    const output = parseQueueBody(tinysdInput, "tiny_sd")
    expect(output).toEqual(tinysdExpected)
  })
  test("missing-prompt", () => {
    const output = parseQueueBody(missingInput, "flux2_klein9b")
    expect(output).toBe(missingExpected)
  })
  test("unknown-contract", () => {
    const output = parseQueueBody(unknownInput, "nope")
    expect(output).toBe(unknownExpected)
  })
})
