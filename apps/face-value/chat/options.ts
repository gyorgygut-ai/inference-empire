"use client"

import { chatFetcher } from "./options/fetcher"
import { presentOutcomeOptionsDef } from "@inference/ui/chat/tools/presentOutcomeOptions"
import { presentImageUploadDef } from "@inference/ui/chat/tools/presentImageUpload"
import { runGenerateImageDef } from "@inference/ui/chat/tools/runGenerateImage"

export const chatOptions = {
  fetcher: chatFetcher,
  tools: [
    presentOutcomeOptionsDef.client(),
    presentImageUploadDef.client(),
    runGenerateImageDef.client(),
  ],
}

export type ChatOptions = typeof chatOptions