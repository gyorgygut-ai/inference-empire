import { toolDefinition } from "@tanstack/ai"

export const presentImageUploadDef = toolDefinition({
  name: "presentImageUpload",
  description: "Present image upload dropzone for the reference image",
  inputSchema: {
    type: "object",
    properties: {},
  },
  outputSchema: {
    type: "object",
    properties: {
      base64: { type: "string" },
      mimeType: { type: "string" },
    },
    required: ["base64", "mimeType"],
  },
})
