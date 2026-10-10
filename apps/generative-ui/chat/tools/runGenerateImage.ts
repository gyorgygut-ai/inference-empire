import { toolDefinition } from "@tanstack/ai"

export const runGenerateImageDef = toolDefinition({
  name: "runGenerateImage",
  description: "Generate image from the selected outcome prompt and reference image",
  needsApproval: true,
  inputSchema: {
    type: "object",
    properties: {
      outcomeId: { type: "string" },
      base64: { type: "string" },
      mimeType: { type: "string" },
    },
    required: ["outcomeId", "base64", "mimeType"],
  },
  outputSchema: {
    type: "object",
    properties: {
      presignedUrl: { type: "string" },
    },
    required: ["presignedUrl"],
  },
})
