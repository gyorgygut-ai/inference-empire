import { toolDefinition, getFile } from "@tanstack/ai";
import { z } from "zod";
import { generateImage } from "@/app/actions/generate";
import { flux2Files, getFlux2FileBlob } from "@/lib/flux2-files-adapter";

const generateImageDefinition = toolDefinition({
  name: "generateImage",
  description: "Generate an image from a reference image and outcome prompt",
  inputSchema: z.object({
    outcomeId: z.string(),
    referenceFileId: z.string(),
    width: z.number().optional(),
    height: z.number().optional(),
  }),
  outputSchema: z.object({
    imageUrl: z.string().url(),
    width: z.number(),
    height: z.number(),
  }),
});

export const generateImageTool = generateImageDefinition.client(async (args) => {
  const handle = await getFile({ adapter: flux2Files, id: args.referenceFileId });
  const blob = getFlux2FileBlob(handle.id);
  if (!blob) {
    throw new Error("Reference image required");
  }
  const file =
    blob instanceof File
      ? blob
      : new File([blob], handle.filename ?? "reference.jpg", {
          type: handle.mimeType ?? blob.type,
        });

  const response = await generateImage(args.outcomeId, file);

  if (response.status === "rejected") {
    throw new Error("Generation rejected");
  }

  return {
    imageUrl: response.presignedUrl,
    width: args.width ?? 512,
    height: args.height ?? 768,
  };
});
