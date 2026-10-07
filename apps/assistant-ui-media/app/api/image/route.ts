import { inferWithPolling } from "@inference/worker-router-client";

export const maxDuration = 60;

const POLL_INTERVAL_MS = 3000;
const TIMEOUT_MS = 50 * 1000;

function parseSize(size: `${number}x${number}` | undefined): {
  width?: number;
  height?: number;
} {
  if (!size) {
    return {};
  }
  const match = /^(\d+)x(\d+)$/.exec(size);
  if (!match) {
    return {};
  }
  return { width: Number(match[1]), height: Number(match[2]) };
}

export async function POST(req: Request) {
  const { prompt, size, seed, model = "flux2" } = (await req.json()) as {
    prompt?: string;
    size?: `${number}x${number}`;
    seed?: number;
    model?: "flux2" | "krea2";
  };
  if (!prompt) {
    return Response.json({ error: "Missing prompt" }, { status: 400 });
  }
  if (model !== "flux2" && model !== "krea2") {
    return Response.json({ error: "Unknown model" }, { status: 400 });
  }

  const prefix = model === "krea2" ? "KREA2" : "FLUX2";
  const baseUrl = (process.env[`${prefix}_ROUTER_URL`] || "").replace(/\/+$/, "");
  const token = process.env[`${prefix}_ROUTER_TOKEN`] || "";

  if (!baseUrl || !token) {
    return Response.json(
      { error: `${prefix}_ROUTER_URL and ${prefix}_ROUTER_TOKEN must be configured` },
      { status: 503 },
    );
  }

  let output: { artifact?: { presigned_url?: string } };
  try {
    output = await inferWithPolling<{ artifact?: { presigned_url?: string } }>(
      {
        prompt,
        ...parseSize(size),
        ...(seed !== undefined && { seed }),
      },
      {
        baseUrl,
        token,
        pollIntervalMs: POLL_INTERVAL_MS,
        timeoutMs: TIMEOUT_MS,
      },
    );
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Inference failed";
    if (message.includes("timeout after")) {
      return Response.json({ error: message }, { status: 504 });
    }
    return Response.json({ error: message || "Inference failed" }, { status: 502 });
  }

  const presignedUrl = output?.artifact?.presigned_url;
  if (!presignedUrl) {
    return Response.json(
      { error: "Inference completed without artifact" },
      { status: 502 },
    );
  }
  return Response.json({
    image: presignedUrl,
    metadata: {},
  });
}
