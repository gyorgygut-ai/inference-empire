import { toolDefinition } from "@tanstack/ai";
import { z } from "zod";

export const generateImageTool = toolDefinition({
  name: "generateImage",
  description: "Generate an image from a reference image and outcome prompt",
  inputSchema: z.object({
    outcomeId: z.string(),
    outcomePrompt: z.string(),
    referenceImage: z.instanceof(File),
  }),
  outputSchema: z.object({
    imageUrl: z.string().url(),
    width: z.number(),
    height: z.number(),
  }),
});
