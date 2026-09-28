import { ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE } from "@/constants"
import { ActionError } from "@/app/types"

export interface OutcomeSummary {
  id: string;
  title: string;
}

export interface AttachmentMeta {
  type: string;
  size: number;
}

export function validateAttachmentMeta(meta: AttachmentMeta): ActionError | null {
  if (!ALLOWED_IMAGE_TYPES.includes(meta.type)) {
    return ActionError.INPUT_IMAGE_TYPE_NOT_ALLOWED
  }
  if (meta.size > MAX_FILE_SIZE) {
    return ActionError.INPUT_IMAGE_TOO_LARGE
  }
  return null
}

export function isGenerateEnabled(selectedOutcomeId: string | null, hasAttachment: boolean): boolean {
  return selectedOutcomeId !== null && selectedOutcomeId !== "" && hasAttachment
}

export function step2Prompt(outcome: OutcomeSummary): string {
  return `Selected "${outcome.title}". Attach a reference photo below, then press Generate.`
}

export function selectionChanged(previousOutcomeId: string | null, nextOutcomeId: string | null): boolean {
  return previousOutcomeId !== nextOutcomeId
}
