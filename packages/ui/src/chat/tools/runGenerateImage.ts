import { toolDefinition } from "@tanstack/ai"
import { z } from "zod"

export const runGenerateImageDef = toolDefinition({
  name: "runGenerateImage",
  description: "Generate image from the selected outcome prompt and reference image",
  needsApproval: true,
  inputSchema: z.object({
    outcomeId: z.string(),
    base64: z.string(),
    mimeType: z.string(),
  }),
  outputSchema: z.object({
    presignedUrl: z.string(),
  }),
})