import { describe, it, expect, vi, beforeEach } from "vitest"
import { requestOutcome, ActionResult } from "@/app/actions"
import { ActionError } from "@/app/types"

vi.mock("@/outcomes", () => ({
  getInferenceOutcome: vi.fn(),
}))

vi.mock("@/app/inference-api", () => ({
  runInferenceWithPolling: vi.fn(),
}))

vi.mock("sharp", () => ({
  default: vi.fn(() => ({
    resize: vi.fn().mockReturnThis(),
    toBuffer: vi.fn().mockResolvedValue(Buffer.from("mock")),
  })),
}))

const { getInferenceOutcome } = await import("@/outcomes")
const { runInferenceWithPolling } = await import("@/app/inference-api")

function createFormData(overrides: Record<string, unknown> = {}): FormData {
  const formData = new FormData()
  formData.append("image", new File(["content"], "test.jpg", { type: "image/jpeg" }))
  formData.append("outcomeId", "valid-outcome")
  Object.entries(overrides).forEach(([key, value]) => {
    formData.append(key, value as string)
  })
  return formData
}

describe("requestOutcome", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns error when image is missing", async () => {
    const formData = new FormData()
    formData.append("outcomeId", "valid-outcome")
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.INPUT_IMAGE_MISSING })
  })

  it("returns error when image type is not allowed", async () => {
    const formData = createFormData()
    formData.set("image", new File(["content"], "test.txt", { type: "text/plain" }))
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.INPUT_IMAGE_TYPE_NOT_ALLOWED })
  })

  it("returns error when image exceeds max size", async () => {
    const bigFile = new File(["x".repeat(10 * 1024 * 1024)], "big.jpg", { type: "image/jpeg" })
    const formData = createFormData()
    formData.set("image", bigFile)
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.INPUT_IMAGE_TOO_LARGE })
  })

  it("returns error when outcomeId is missing", async () => {
    const formData = createFormData()
    formData.delete("outcomeId")
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.OUTCOME_MISSING })
  })

  it("returns error when outcomeId is invalid", async () => {
    vi.mocked(getInferenceOutcome).mockReturnValue(null)
    const formData = createFormData()
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.OUTCOME_INVALID })
  })

  it("returns imageUrl on successful inference", async () => {
    vi.mocked(getInferenceOutcome).mockReturnValue({
      id: "valid-outcome",
      title: "Test",
      prompt: "test prompt",
      width: 1024,
      height: 1024,
    })
    vi.mocked(runInferenceWithPolling).mockResolvedValue({
      output: { artifact: { presigned_url: "https://example.com/image.png" } },
    })
    const formData = createFormData()
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ imageUrl: "https://example.com/image.png" })
  })

  it("returns error on server timeout", async () => {
    vi.mocked(getInferenceOutcome).mockReturnValue({
      id: "valid-outcome",
      title: "Test",
      prompt: "test prompt",
      width: 1024,
      height: 1024,
    })
    vi.mocked(runInferenceWithPolling).mockRejectedValue(new Error("timeout"))
    const formData = createFormData()
    const result = await requestOutcome(null, formData)
    expect(result).toEqual({ error: ActionError.SERVER_TIMEOUT })
  })
})
