import "server-only"

const unavailable = () =>
  Response.json({ error: "Voice worker is not configured" }, { status: 503 })

export async function POST(request: Request) {
  const workerUrl = process.env.WORKER_URL
  const beamToken = process.env.BEAM_TOKEN

  if (!workerUrl || !beamToken) return unavailable()

  try {
    const response = await fetch(`${workerUrl.replace(/\/$/, "")}/webrtc/offer`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${beamToken}`,
        "Content-Type": "application/json",
      },
      body: await request.text(),
      cache: "no-store",
    })
    const body = await response.text()

    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    })
  } catch {
    return Response.json({ error: "Voice worker request failed" }, { status: 502 })
  }
}
