import manifest from "@/lib/manifest.json"

type Status = "unknown" | "healthy" | "unhealthy" | "deployed"

export async function GET() {
  const beamToken = process.env.BEAM_TOKEN
  const runpodKey = process.env.RUNPOD_API_KEY
  const modalTokenId = process.env.MODAL_TOKEN_ID
  const modalTokenSecret = process.env.MODAL_TOKEN_SECRET

  const hasBeam = Boolean(beamToken)
  const hasRunpod = Boolean(runpodKey)
  const hasModal = Boolean(modalTokenId && modalTokenSecret)

  const workers: { stem: string; status: Status }[] = []

  for (const w of manifest.workers) {
    let status: Status = "unknown"

    if (w.platform === "beam" && hasBeam) {
      status = await probeBeam(beamToken as string)
    } else if (w.platform === "flash" && hasRunpod) {
      status = await probeRunpod(runpodKey as string)
    } else if (w.platform === "modal" && hasModal) {
      status = await probeModal()
    }

    workers.push({ stem: w.stem, status })
  }

  return Response.json({ workers })
}

async function probeBeam(token: string): Promise<Status> {
  try {
    const res = await fetch("https://api.beam.cloud/v2/stub", {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(2000),
    })
    if (res.ok) return "healthy"
    if (res.status >= 400 && res.status < 500) return "deployed"
    return "unhealthy"
  } catch {
    return "unknown"
  }
}

async function probeRunpod(key: string): Promise<Status> {
  try {
    const res = await fetch("https://api.runpod.io/v2/endpoints", {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(2000),
    })
    if (res.ok) return "healthy"
    if (res.status >= 400 && res.status < 500) return "deployed"
    return "unhealthy"
  } catch {
    return "unknown"
  }
}

async function probeModal(): Promise<Status> {
  try {
    const res = await fetch("https://api.modal.com/", {
      signal: AbortSignal.timeout(2000),
    })
    if (res.ok) return "healthy"
    return "deployed"
  } catch {
    return "unknown"
  }
}
