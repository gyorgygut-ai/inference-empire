import { ActionError } from "@/app/types"
import { vocabulary } from "@/app/vocabulary"
import type {
  CompleteAttachment,
  ThreadAssistantMessagePart,
  ThreadUserMessagePart,
} from "@assistant-ui/react"
import { validateAttachmentMeta } from "./chat-flow"

export type GenerateResult = { imageUrl: string } | { error: ActionError };

export type RunAction = (formData: FormData) => Promise<GenerateResult>;

export interface SubmitResult {
  content: ThreadAssistantMessagePart[];
  imageUrl: string | null;
}

export function errorTextFor(error: ActionError): string {
  switch (error) {
    case ActionError.SERVER_TIMEOUT:
      return vocabulary.errors.timeout
    case ActionError.OUTCOME_MISSING:
    case ActionError.OUTCOME_INVALID:
      return vocabulary.errors.outcomeInvalid
    case ActionError.INPUT_IMAGE_MISSING:
      return vocabulary.errors.imageMissing
    case ActionError.INPUT_IMAGE_TOO_LARGE:
      return vocabulary.errors.imageTooLarge
    case ActionError.INPUT_IMAGE_TYPE_NOT_ALLOWED:
      return vocabulary.errors.imageType
  }
}

export function assistantContentForResult(result: GenerateResult): SubmitResult {
  if ("imageUrl" in result) {
    return {
      content: [{ type: "image", image: result.imageUrl }],
      imageUrl: result.imageUrl,
    }
  }
  return {
    content: [{ type: "text", text: errorTextFor(result.error) }],
    imageUrl: null,
  }
}

export function buildFormData(outcomeId: string, file: File): FormData {
  const formData = new FormData()
  formData.append("image", file)
  formData.append("outcomeId", outcomeId)
  return formData
}

export async function urlToFile(url: string, name: string): Promise<File> {
  const response = await fetch(url)
  const blob = await response.blob()
  return new File([blob], name, { type: blob.type })
}

function isImagePart(part: ThreadUserMessagePart): part is Extract<ThreadUserMessagePart, { type: "image" }> {
  return part.type === "image"
}

export async function fileFromAttachment(attachment: CompleteAttachment): Promise<File | null> {
  if (attachment.file instanceof File) {
    return attachment.file
  }
  const imagePart = attachment.content.find(isImagePart)
  if (imagePart && typeof imagePart.image === "string") {
    return urlToFile(imagePart.image, attachment.name || "reference.png")
  }
  return null
}

export async function submitFlow(
  outcomeId: string | null,
  file: File | null,
  runAction: RunAction,
): Promise<SubmitResult> {
  if (!outcomeId) {
    return {
      content: [{ type: "text", text: vocabulary.outcomePicker.missingSelection }],
      imageUrl: null,
    }
  }
  if (!file) {
    return {
      content: [{ type: "text", text: vocabulary.errors.imageMissing }],
      imageUrl: null,
    }
  }
  const metaError = validateAttachmentMeta({ type: file.type, size: file.size })
  if (metaError) {
    return {
      content: [{ type: "text", text: errorTextFor(metaError) }],
      imageUrl: null,
    }
  }
  const result = await runAction(buildFormData(outcomeId, file))
  return assistantContentForResult(result)
}
