import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, test, expect } from "vitest"
import {
  buildFormData,
  submitFlow,
  urlToFile,
  type GenerateResult,
  type SubmitResult,
} from "../chat-adapter"
import { createRunActionStub, type CallCounter } from "./stubs/run-action-stub"

const fixturesDir = join(import.meta.dirname, "fixtures")

function read<T>(path: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, path), "utf-8"))
}

function makeFile(name: string, type: string, size: number): File {
  return new File(["x".repeat(size)], name, { type })
}

interface FileInput {
  outcomeId: string
  fileName: string
  fileType: string
  fileSize: number
}

describe("submitFlow", () => {
  test("submit-success", async () => {
    const input = read<FileInput>("submit-success/input.json")
    const stubResult = read<GenerateResult>("submit-success/stubs/success-result.json")
    const expected = read<SubmitResult>("submit-success/expected.json")
    const output = await submitFlow(
      input.outcomeId,
      makeFile(input.fileName, input.fileType, input.fileSize),
      createRunActionStub(stubResult),
    )
    expect(output).toEqual(expected)
  })

  test("submit-missing-outcome", async () => {
    const expected = read<SubmitResult>("submit-missing-outcome/expected.json")
    const counter: CallCounter = { count: 0 }
    const output = await submitFlow(
      null,
      null,
      createRunActionStub({ imageUrl: "https://r2.example/never.png" }, counter),
    )
    expect(output).toEqual(expected)
    expect(counter.count).toBe(0)
  })

  test("submit-missing-file", async () => {
    const input = read<{ outcomeId: string }>("submit-missing-file/input.json")
    const expected = read<SubmitResult>("submit-missing-file/expected.json")
    const counter: CallCounter = { count: 0 }
    const output = await submitFlow(
      input.outcomeId,
      null,
      createRunActionStub({ imageUrl: "https://r2.example/never.png" }, counter),
    )
    expect(output).toEqual(expected)
    expect(counter.count).toBe(0)
  })

  test("submit-oversized", async () => {
    const input = read<FileInput>("submit-oversized/input.json")
    const expected = read<SubmitResult>("submit-oversized/expected.json")
    const counter: CallCounter = { count: 0 }
    const output = await submitFlow(
      input.outcomeId,
      makeFile(input.fileName, input.fileType, input.fileSize),
      createRunActionStub({ imageUrl: "https://r2.example/never.png" }, counter),
    )
    expect(output).toEqual(expected)
    expect(counter.count).toBe(0)
  })

  test("submit-timeout", async () => {
    const input = read<FileInput>("submit-timeout/input.json")
    const stubResult = read<GenerateResult>("submit-timeout/stubs/timeout-result.json")
    const expected = read<SubmitResult>("submit-timeout/expected.json")
    const output = await submitFlow(
      input.outcomeId,
      makeFile(input.fileName, input.fileType, input.fileSize),
      createRunActionStub(stubResult),
    )
    expect(output).toEqual(expected)
  })

  test("submit-outcome-invalid", async () => {
    const input = read<FileInput>("submit-outcome-invalid/input.json")
    const stubResult = read<GenerateResult>("submit-outcome-invalid/stubs/outcome-invalid-result.json")
    const expected = read<SubmitResult>("submit-outcome-invalid/expected.json")
    const output = await submitFlow(
      input.outcomeId,
      makeFile(input.fileName, input.fileType, input.fileSize),
      createRunActionStub(stubResult),
    )
    expect(output).toEqual(expected)
  })
})

describe("urlToFile", () => {
  test("url-to-file", async () => {
    const input = read<{ dataUrl: string; name: string }>("url-to-file/input.json")
    const expected = read<{ name: string; type: string; size: number }>("url-to-file/expected.json")
    const file = await urlToFile(input.dataUrl, input.name)
    expect({ name: file.name, type: file.type, size: file.size }).toEqual(expected)
  })
})

describe("buildFormData", () => {
  test("build-form-data", () => {
    const input = read<FileInput>("build-form-data/input.json")
    const expected = read<FileInput>("build-form-data/expected.json")
    const formData = buildFormData(input.outcomeId, makeFile(input.fileName, input.fileType, input.fileSize))
    const file = formData.get("image") as File
    expect({
      outcomeId: formData.get("outcomeId"),
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size,
    }).toEqual(expected)
  })
})
