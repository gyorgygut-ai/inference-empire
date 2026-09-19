import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import { runOutcomeWithDeps } from "@/app/actions"
import { createOutcomeStub, type OutcomeInput } from "./stubs/outcomes-stub"

const fixturesDir = join(import.meta.dirname, "fixtures")

function read<T>(path: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, path), "utf-8"))
}

function makeFormData(input: { fileName: string; fileType: string; fileSize: number; outcomeId: string }): FormData {
  const formData = new FormData()
  formData.append("image", new File(["x".repeat(input.fileSize)], input.fileName, { type: input.fileType }))
  formData.append("outcomeId", input.outcomeId)
  return formData
}

describe("validation", () => {
  const mockOutcome: OutcomeInput = { prompt: "test", width: 1024, height: 1024 }
  const mockInferenceResult = { output: { artifact: { presigned_url: "https://r2/x.png" } } }

  test("missing-image", async () => {
    const input = read<{ outcomeId: string }>("validation/missing-image/input.json")
    const expected = read<{ error: string }>("validation/missing-image/expected.json")
    const formData = new FormData()
    formData.append("outcomeId", input.outcomeId)
    const result = await runOutcomeWithDeps(null, formData, () => mockOutcome, async () => Buffer.from(""), async () => mockInferenceResult)
    expect((result as { error: string }).error).toBe(expected.error)
  })

  test("invalid-type", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("validation/invalid-type/input.json")
    const expected = read<{ error: string }>("validation/invalid-type/expected.json")
    const formData = makeFormData(input)
    const result = await runOutcomeWithDeps(null, formData, () => mockOutcome, async () => Buffer.from(""), async () => mockInferenceResult)
    expect((result as { error: string }).error).toBe(expected.error)
  })

  test("oversized", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("validation/oversized/input.json")
    const expected = read<{ error: string }>("validation/oversized/expected.json")
    const formData = makeFormData(input)
    const result = await runOutcomeWithDeps(null, formData, () => mockOutcome, async () => Buffer.from(""), async () => mockInferenceResult)
    expect((result as { error: string }).error).toBe(expected.error)
  })

  test("missing-outcome", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("validation/missing-outcome/input.json")
    const expected = read<{ error: string }>("validation/missing-outcome/expected.json")
    const formData = makeFormData(input)
    const result = await runOutcomeWithDeps(null, formData, () => null, async () => Buffer.from(""), async () => mockInferenceResult)
    expect((result as { error: string }).error).toBe(expected.error)
  })

  test("invalid-outcome", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("validation/invalid-outcome/input.json")
    const expected = read<{ error: string }>("validation/invalid-outcome/expected.json")
    const formData = makeFormData(input)
    const result = await runOutcomeWithDeps(null, formData, () => null, async () => Buffer.from(""), async () => mockInferenceResult)
    expect((result as { error: string }).error).toBe(expected.error)
  })
})

describe("inference", () => {
  test("success/inference", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("success/inference/input.json")
    const stubs = read<{ outcomes: Record<string, OutcomeInput>; inference: { output: { artifact: { presigned_url: string } } } }>("success/inference/stubs/composite.json")
    const expected = read<{ imageUrl: string }>("success/inference/expected.json")
    const formData = makeFormData(input)
    const outcomeMap: Record<string, OutcomeInput | null> = { "valid-outcome": stubs.outcomes["valid-outcome"] }
    const result = await runOutcomeWithDeps(
      null,
      formData,
      createOutcomeStub(outcomeMap),
      async () => Buffer.from("mock"),
      () => Promise.resolve(stubs.inference)
    )
    expect(result).toEqual(expected)
  })

  test("error/inference-timeout", async () => {
    const input = read<{ fileName: string; fileType: string; fileSize: number; outcomeId: string }>("error/inference-timeout/input.json")
    const stubs = read<{ outcomes: Record<string, OutcomeInput>; inference: { error: string } }>("error/inference-timeout/stubs/composite.json")
    const expected = read<{ error: string }>("error/inference-timeout/expected.json")
    const formData = makeFormData(input)
    const outcomeMap: Record<string, OutcomeInput | null> = { "valid-outcome": stubs.outcomes["valid-outcome"] }
    const result = await runOutcomeWithDeps(
      null,
      formData,
      createOutcomeStub(outcomeMap),
      async () => Buffer.from("mock"),
      () => { throw new Error(stubs.inference.error) }
    )
    expect((result as { error: string }).error).toBe(expected.error)
  })
})
