import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import {
  isGenerateEnabled,
  selectionChanged,
  step2Prompt,
  validateAttachmentMeta,
  type AttachmentMeta,
  type OutcomeSummary,
} from "../chat-flow"

const fixturesDir = join(import.meta.dirname, "fixtures")

function read<T>(path: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, path), "utf-8"))
}

describe("step2-prompt", () => {
  test("step2-prompt", () => {
    const input = read<OutcomeSummary>("step2-prompt/input.json")
    const expected = read<string>("step2-prompt/expected.json")
    expect(step2Prompt(input)).toBe(expected)
  })
})

describe("isGenerateEnabled", () => {
  test("generate-enabled", () => {
    const input = read<{ outcomeId: string | null; hasAttachment: boolean }>("generate-enabled/input.json")
    const expected = read<{ enabled: boolean }>("generate-enabled/expected.json")
    expect(isGenerateEnabled(input.outcomeId, input.hasAttachment)).toBe(expected.enabled)
  })

  test("generate-disabled-no-outcome", () => {
    const input = read<{ outcomeId: string | null; hasAttachment: boolean }>("generate-disabled-no-outcome/input.json")
    const expected = read<{ enabled: boolean }>("generate-disabled-no-outcome/expected.json")
    expect(isGenerateEnabled(input.outcomeId, input.hasAttachment)).toBe(expected.enabled)
  })

  test("generate-disabled-no-attachment", () => {
    const input = read<{ outcomeId: string | null; hasAttachment: boolean }>("generate-disabled-no-attachment/input.json")
    const expected = read<{ enabled: boolean }>("generate-disabled-no-attachment/expected.json")
    expect(isGenerateEnabled(input.outcomeId, input.hasAttachment)).toBe(expected.enabled)
  })
})

describe("validateAttachmentMeta", () => {
  test("validate-ok", () => {
    const input = read<AttachmentMeta>("validate-ok/input.json")
    const expected = read<{ error: string | null }>("validate-ok/expected.json")
    expect(validateAttachmentMeta(input)).toBe(expected.error)
  })

  test("validate-invalid-type", () => {
    const input = read<AttachmentMeta>("validate-invalid-type/input.json")
    const expected = read<{ error: string }>("validate-invalid-type/expected.json")
    expect(validateAttachmentMeta(input)).toBe(expected.error)
  })

  test("validate-oversized", () => {
    const input = read<AttachmentMeta>("validate-oversized/input.json")
    const expected = read<{ error: string }>("validate-oversized/expected.json")
    expect(validateAttachmentMeta(input)).toBe(expected.error)
  })
})

describe("selectionChanged", () => {
  test("selection-changed", () => {
    const input = read<{ previous: string | null; next: string | null }>("selection-changed/input.json")
    const expected = read<{ changed: boolean }>("selection-changed/expected.json")
    expect(selectionChanged(input.previous, input.next)).toBe(expected.changed)
  })

  test("selection-unchanged", () => {
    const input = read<{ previous: string | null; next: string | null }>("selection-unchanged/input.json")
    const expected = read<{ changed: boolean }>("selection-unchanged/expected.json")
    expect(selectionChanged(input.previous, input.next)).toBe(expected.changed)
  })
})
