import { BaseImageAdapter, type ImageAdapterConfig } from "@tanstack/ai/adapters";
import { type ImageGenerationOptions, type ImageGenerationResult } from "@tanstack/ai";
import { generateImage } from "@/app/actions/generate";
import { getInferenceOutcome } from "@/outcomes/inference-outcomes";
import { getFlux2FileBlob } from "@/lib/flux2-files-adapter";
import { randomUUID } from "crypto";

export class Flux2KleinAdapter extends BaseImageAdapter {
  readonly name = "flux2-klein";
  readonly model = "flux-2-klein" as const;
  readonly supportsFileSources = true;

  constructor(config: ImageAdapterConfig = {}) {
    super("flux-2-klein", config);
  }

  async generateImages(options: ImageGenerationOptions): Promise<ImageGenerationResult> {
    const outcomeId = (options.modelOptions as { outcomeId?: string } | undefined)?.outcomeId;
    const outcome = outcomeId ? getInferenceOutcome(outcomeId) : null;
    if (!outcome) {
      throw new Error("Unknown outcome");
    }

    const imagePart =
      Array.isArray(options.prompt) ? (options.prompt as any[]).find((p) => p.type === "image") : undefined;
    const file = await this.resolveReferenceImage(imagePart);

    if (!file) {
      throw new Error("Reference image required");
    }

    const response = await generateImage(outcome.id, file);

    if (response.status === "rejected") {
      throw new Error("Generation rejected");
    }

    return {
      id: randomUUID(),
      model: this.model,
      images: [{ url: response.presignedUrl }],
    };
  }

  private async resolveReferenceImage(imagePart: any): Promise<File | null> {
    if (!imagePart?.source) {
      return null;
    }
    if (imagePart.source.type === "file" && typeof imagePart.source.value === "string") {
      const blob = getFlux2FileBlob(imagePart.source.value);
      if (!blob) {
        return null;
      }
      return blob instanceof File
        ? blob
        : new File([blob], "reference.jpg", { type: blob.type || "image/jpeg" });
    }
    if (imagePart.source.type === "data" && typeof imagePart.source.value === "string") {
      const blob = await (await fetch(imagePart.source.value)).blob();
      return new File([blob], "reference.jpg", { type: blob.type || "image/jpeg" });
    }
    return null;
  }
}

export const flux2KleinAdapter = new Flux2KleinAdapter();
