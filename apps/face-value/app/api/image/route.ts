import { generateImage, toServerSentEventsResponse } from "@tanstack/ai";
import { flux2KleinAdapter } from "@/lib/flux2-adapter";

export const dynamic = "force-dynamic";

type ImageRequestBody = {
  data?: {
    prompt?: unknown;
    size?: string;
    numberOfImages?: number;
    modelOptions?: Record<string, unknown>;
  };
  prompt?: unknown;
  size?: string;
  numberOfImages?: number;
  modelOptions?: Record<string, unknown>;
};

export const POST = async (request: Request): Promise<Response> => {
  const body = (await request.json()) as ImageRequestBody;
  const data = body.data ?? body;

  const stream = generateImage({
    adapter: flux2KleinAdapter,
    prompt: data.prompt as never,
    size: data.size,
    numberOfImages: data.numberOfImages,
    modelOptions: data.modelOptions as never,
    stream: true,
  });

  return toServerSentEventsResponse(stream);
};
