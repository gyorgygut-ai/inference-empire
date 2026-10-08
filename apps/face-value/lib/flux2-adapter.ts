import { BaseImageAdapter, type ImageAdapterConfig } from "@tanstack/ai/adapters";
import { generateImage } from "@/app/actions/generate";

export class Flux2KleinAdapter extends BaseImageAdapter {
  readonly name = "flux2-klein";
  readonly model = "flux-2-klein" as const;
  readonly supportsFileSources = true;

  constructor(config: ImageAdapterConfig = {}) {
    super("flux-2-klein", config);
  }

  async generateImages(options: any): Promise<any> {
    let prompt = "";
    let referenceImage: string | undefined;

    if (typeof options.prompt === "string") {
      prompt = options.prompt;
    } else if (Array.isArray(options.prompt)) {
      const textPart = options.prompt.find((p: any) => p.type === "text");
      const imagePart = options.prompt.find((p: any) => p.type === "image");
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
