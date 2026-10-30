import "server-only"

export async function GET() {
  const workerUrl = process.env.WORKER_URL
  const beamToken = process.env.BEAM_TOKEN
  if (!workerUrl || !beamToken) {
    return Response.json({ error: "Voice worker is not configured" }, { status: 503 })
  }

  try {
    const response = await fetch(`${workerUrl.replace(/\/$/, "")}/health`, {
      headers: { Authorization: `Bearer ${beamToken}` },
      cache: "no-store",
    })
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    })
  } catch {
    return Response.json({ error: "Voice worker heartbeat failed" }, { status: 502 })
  }
}
