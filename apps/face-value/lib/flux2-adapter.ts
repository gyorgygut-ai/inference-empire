import { BaseImageAdapter, type ImageAdapterConfig } from "@tanstack/ai/adapters";
import { type ImageGenerationOptions, type ImageGenerationResult } from "@tanstack/ai";
import { generateImage } from "@/app/actions/generate";
import { randomUUID } from "crypto";

export class Flux2KleinAdapter extends BaseImageAdapter {
  readonly name = "flux2-klein";
  readonly model = "flux-2-klein" as const;
  readonly supportsFileSources = true;

  constructor(config: ImageAdapterConfig = {}) {
    super("flux-2-klein", config);
  }

  async generateImages(options: ImageGenerationOptions): Promise<ImageGenerationResult> {
    let prompt = "";
    let referenceImage: string | undefined;

    if (typeof options.prompt === "string") {
      prompt = options.prompt;
    } else if (Array.isArray(options.prompt)) {
      const parts = options.prompt as any[];
      const textPart = parts.find((p) => p.type === "text");
      const imagePart = parts.find((p) => p.type === "image");
      prompt = textPart?.content || "";
      referenceImage = imagePart?.source?.value;
    }

    const outcomeId = this.extractOutcomeId(prompt);
    const file = referenceImage ? await this.dataUrlToFile(referenceImage) : null;
    
    if (!file) {
      throw new Error("Reference image required");
    }

    const response = await generateImage(outcomeId, file);

    if (response.status === "rejected") {
      throw new Error("Generation rejected");
    }

    return {
      id: randomUUID(),
      model: this.model,
      images: [{ url: response.presignedUrl }],
    };
  }

  private extractOutcomeId(prompt: string): string {
    return "celebrity-selfie";
  }

  private async dataUrlToFile(dataUrl: string): Promise<File> {
    const arr = dataUrl.split(",");
    const mime = arr[0].match(/:(.*?);/)?.[1] || "image/jpeg";
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) u8arr[n] = bstr.charCodeAt(n);
    return new File([u8arr], "reference.jpg", { type: mime });
  }
}

export const flux2KleinAdapter = new Flux2KleinAdapter();
