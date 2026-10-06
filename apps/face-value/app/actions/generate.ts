"use server";

import sharp from "sharp";
import { inferWithPolling } from "@inference/worker-router-client";
import type { Flux2Klein9BOutput } from "@/app/inference-api/schema";
import { workerRouterConfig } from "@/app/inference-api/router-config";
import { getInferenceOutcome } from "@/outcomes";

const MAX_SIZE = 512;
const MAX_BYTES = 5 * 1024 * 1024;

export type GenerateImageResult =
  { status: "done"; presignedUrl: string } | { status: "rejected" };

export async function generateImage(
  outcomeId: string,
  imageFile: File,
): Promise<GenerateImageResult> {
  if (!imageFile) {
    return { status: "rejected" };
  }
  if (imageFile.size > MAX_BYTES) {
    return { status: "rejected" };
  }
  if (!imageFile.type.startsWith("image/")) {
    return { status: "rejected" };
  }

  const buffer = Buffer.from(await imageFile.arrayBuffer());
  const resized = await sharp(buffer)
    .resize({ width: MAX_SIZE, height: MAX_SIZE, fit: "inside" })
    .toBuffer();
  const base64 = resized.toString("base64");

  const outcome = getInferenceOutcome(outcomeId);
  if (!outcome) {
    return { status: "rejected" };
  }

  const input = {
    prompt: outcome.prompt,
    width: outcome.width,
    height: outcome.height,
    input_image: base64,
  };

  try {
    const output = await inferWithPolling<Flux2Klein9BOutput>(input, {
      baseUrl: workerRouterConfig.baseUrl,
      token: workerRouterConfig.authToken,
      pollIntervalMs: 3000,
      timeoutMs: 60000 * 3,
    });
    return { status: "done", presignedUrl: output.artifact.presigned_url };
  } catch {
    return { status: "rejected" };
  }
}
