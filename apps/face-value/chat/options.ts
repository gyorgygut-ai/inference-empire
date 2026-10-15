"use client"

import { presentOutcomeOptionsDef } from "./tools/presentOutcomeOptions/definition"
import { presentImageUploadDef } from "./tools/presentImageUpload/definition"
import { runGenerateImageDef } from "./tools/runGenerateImage/definition"

const chatFetcher = async () => {
  throw new Error("Append-only chat: no LLM transport")
}

export const chatOptions = {
  fetcher: chatFetcher,
  tools: [
    presentOutcomeOptionsDef.client(),
    presentImageUploadDef.client(),
    runGenerateImageDef.client(),
  ],
}

export type ChatOptions = typeof chatOptions
