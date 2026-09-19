import { describe, test, expect } from "vitest"
import { verifyToken } from "../src/auth"
import validInput from "./fixtures/auth/valid/input.json"
import validExpected from "./fixtures/auth/valid/expected.json"
import schemeInput from "./fixtures/auth/wrong-scheme/input.json"
import schemeExpected from "./fixtures/auth/wrong-scheme/expected.json"
import missingInput from "./fixtures/auth/missing/input.json"
import missingExpected from "./fixtures/auth/missing/expected.json"
import mismatchInput from "./fixtures/auth/mismatch/input.json"
import mismatchExpected from "./fixtures/auth/mismatch/expected.json"

describe("auth", () => {
  test("valid", async () => {
    const output = await verifyToken(validInput.header, validInput.secret)
    expect(output).toBe(validExpected)
  })
  test("wrong-scheme", async () => {
    const output = await verifyToken(schemeInput.header, schemeInput.secret)
    expect(output).toBe(schemeExpected)
  })
  test("missing", async () => {
    const output = await verifyToken(missingInput.header, missingInput.secret)
    expect(output).toBe(missingExpected)
  })
  test("mismatch", async () => {
    const output = await verifyToken(mismatchInput.header, mismatchInput.secret)
    expect(output).toBe(mismatchExpected)
  })
})
