"use client"

import { chatFetcher } from "./options/fetcher"
import { presentOutcomeOptionsDef } from "./tools/presentOutcomeOptions"
import { presentImageUploadDef } from "./tools/presentImageUpload"
import { runGenerateImageDef } from "./tools/runGenerateImage"

export const chatOptions = {
  fetcher: chatFetcher,
  tools: [presentOutcomeOptionsDef, presentImageUploadDef, runGenerateImageDef],
}