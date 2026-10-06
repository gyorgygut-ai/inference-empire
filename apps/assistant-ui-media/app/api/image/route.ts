export const maxDuration = 60;

const POLL_INTERVAL_MS = 3000;
const TIMEOUT_MS = 50 * 1000;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function parseSize(size: `${number}x${number}` | undefined): {
  width?: number;
  height?: number;
} {
  if (!size) return {};
  const match = /^(\d+)x(\d+)$/.exec(size);
  if (!match) return {};
  return { width: Number(match[1]), height: Number(match[2]) };
}

async function upstreamErrorText(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const body = JSON.parse(text) as { error?: string };
    return body.error ?? text;
  } catch {
    return text;
  }
}

export async function POST(req: Request) {
  const { prompt, size, seed } = (await req.json()) as {
    prompt?: string;
    size?: `${number}x${number}`;
    seed?: number;
  };
  if (!prompt) {
    return Response.json({ error: "Missing prompt" }, { status: 400 });
  }

  const baseUrl = (process.env.FLUX2_ROUTER_URL || "").replace(/\/+$/, "");
  const token = process.env.FLUX2_ROUTER_TOKEN || "";

  if (!baseUrl || !token) {
    return Response.json(
      { error: "FLUX2_ROUTER_URL and FLUX2_ROUTER_TOKEN must be configured" },
      { status: 503 },
    );
  }

  const headers = {
    Authorization: `Bearer ${token}`,
    "content-type": "application/json",
  };

  const queueRes = await fetch(`${baseUrl}/queue`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      input: {
        prompt,
        ...parseSize(size),
        ...(seed !== undefined && { seed }),
      },
    }),
  });
  if (!queueRes.ok) {
    const message = await upstreamErrorText(queueRes);
    return Response.json(
      { error: message || "Inference submit failed" },
      { status: 502 },
    );
  }
  const { task_id: taskId } = (await queueRes.json()) as { task_id: string };
  if (!taskId) {
    return Response.json(
      { error: "Inference submit failed" },
      { status: 502 },
    );
  }

  const deadline = Date.now() + TIMEOUT_MS;
  for (;;) {
    if (Date.now() >= deadline) {
      return Response.json(
        { error: `timeout after ${TIMEOUT_MS}ms` },
        { status: 504 },
      );
    }
    const taskRes = await fetch(
      `${baseUrl}/task/${encodeURIComponent(taskId)}`,
      { headers },
    );
    if (!taskRes.ok) {
      const message = await upstreamErrorText(taskRes);
      return Response.json(
        { error: message || "Inference poll failed" },
        { status: 502 },
      );
    }
    const task = (await taskRes.json()) as {
      status: string;
      output?: { artifact?: { presigned_url?: string } };
    };
    if (task.status === "DONE") {
      const presignedUrl = task.output?.artifact?.presigned_url;
      if (!presignedUrl) {
        return Response.json(
          { error: "Inference completed without artifact" },
          { status: 502 },
        );
      }
      const imgRes = await fetch(presignedUrl);
      if (!imgRes.ok) {
        return Response.json(
          { error: "Failed to fetch generated image" },
          { status: 502 },
        );
      }
      const mimeType =
        imgRes.headers.get("content-type")?.split(";")[0] || "image/png";
      const buffer = Buffer.from(await imgRes.arrayBuffer());
      return Response.json({
        image: `data:${mimeType};base64,${buffer.toString("base64")}`,
        mimeType,
        metadata: {},
      });
    }
    if (task.status === "REJECTED") {
      return Response.json({ error: "REJECTED" }, { status: 502 });
    }
    await sleep(POLL_INTERVAL_MS);
  }
}
