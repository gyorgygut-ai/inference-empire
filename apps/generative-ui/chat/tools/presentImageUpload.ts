import { toolDefinition } from "@tanstack/ai"
import { z } from "zod"

export const presentImageUploadDef = toolDefinition({
  name: "presentImageUpload",
  description: "Present image upload dropzone for the reference image",
  inputSchema: z.object({
    outcomeId: z.string(),
  }),
  outputSchema: z.object({
    base64: z.string(),
    mimeType: z.string(),
  }),
})
