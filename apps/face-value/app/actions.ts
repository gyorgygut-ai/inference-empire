"use server"

import { MAX_FILE_SIZE, ALLOWED_IMAGE_TYPES } from "@/constants"
import { getInferenceOutcome } from "@/outcomes"
import { runInferenceWithPolling, type Flux2Klein9BInput, type Flux2Klein9BOutput } from "./inference-api"
import { ActionError } from './types'
import sharp from "sharp"

export type ActionResult = { imageUrl: string } | { error: ActionError };

interface OutcomeInput {
  prompt: string
  width?: number
  height?: number
}

async function resizeImage(file: File): Promise<Buffer> {
  const buffer = await file.arrayBuffer()
  return sharp(Buffer.from(buffer))
    .resize(512, 512, { fit: "inside" })
    .toBuffer()
}

export async function runOutcomeWithDeps(
  _prev: ActionResult | null,
  formData: FormData,
  getOutcomeFn: (id: string) => OutcomeInput | null,
  resizeFn: (file: File) => Promise<Buffer>,
  runInferenceFn: (input: Flux2Klein9BInput) => Promise<{ output: Flux2Klein9BOutput }>
): Promise<ActionResult> {
  const file = formData.get("image")

  if (!(file instanceof File) || file.size === 0) {
    return { error: ActionError.INPUT_IMAGE_MISSING }
  }

  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return { error: ActionError.INPUT_IMAGE_TYPE_NOT_ALLOWED }
  }

  if (file.size > MAX_FILE_SIZE) {
    return { error: ActionError.INPUT_IMAGE_TOO_LARGE }
  }

  const outcomeId = formData.get("outcomeId")
  if (typeof outcomeId !== "string" || !outcomeId) {
    return { error: ActionError.OUTCOME_MISSING }
  }

  const outcome = getOutcomeFn(outcomeId)
  if (!outcome) {
    return { error: ActionError.OUTCOME_INVALID }
  }

  const resizedImage = await resizeFn(file)

  try {
    const response = await runInferenceFn({
      ...outcome,
      input_image: resizedImage.toString("base64"),
    })

    return { imageUrl: response.output.artifact.presigned_url }
  } catch {
    return { error: ActionError.SERVER_TIMEOUT }
  }
}

export async function requestOutcome(
  _prev: ActionResult | null,
  formData: FormData,
): Promise<ActionResult> {
  return runOutcomeWithDeps(_prev, formData, getInferenceOutcome, resizeImage, runInferenceWithPolling)
}
