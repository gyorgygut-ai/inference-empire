import { generateImage, toServerSentEventsResponse } from "@tanstack/ai";
import { flux2KleinAdapter } from "@/lib/flux2-adapter";

export async function POST(request: Request) {
  const { prompt } = await request.json();

  const stream = generateImage({
    adapter: flux2KleinAdapter,
    prompt,
    stream: true,
  });

  return toServerSentEventsResponse(stream);
}
