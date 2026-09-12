import manifest from "@/lib/manifest.json"
import { readFileSync } from "fs"
import { join } from "path"

type Status = "unknown" | "healthy" | "unhealthy" | "deployed"

const NAME_PATTERNS = {
  beam: /@(task_queue|endpoint|asgi)\(\s*name="([^"]+)"/,
  flash: /@Endpoint\(\s*name="([^"]+)"/,
  modal: /modal\.App\(\s*"([^"]+)"\s*\)/,
}

function getWorkerName(stem: string): string {
  const platform = stem.startsWith("worker_beam_") ? "beam"
    : stem.startsWith("worker_flash_") ? "flash"
    : stem.startsWith("worker_modal_") ? "modal"
    : null
  if (!platform) return stem
  // workers repo is one level up from gui
  const filePath = join(process.cwd(), "../workers", platform, `${stem}.py`)
  try {
    const src = readFileSync(filePath, "utf8")
    const m = NAME_PATTERNS[platform as keyof typeof NAME_PATTERNS].exec(src)
    return m?.[1] ?? stem
  } catch {
    return stem
  }
}

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
    const name = getWorkerName(w.stem)

    if (w.platform === "beam" && hasBeam) {
      status = await probeBeam(beamToken as string, name)
    } else if (w.platform === "flash" && hasRunpod) {
      status = await probeRunpod(runpodKey as string, name)
    } else if (w.platform === "modal" && hasModal) {
      status = await probeModal(modalTokenId as string, modalTokenSecret as string, name)
    }

    workers.push({ stem: w.stem, status })
  }

  return Response.json({ workers })
}

async function probeBeam(token: string, stem: string): Promise<Status> {
  try {
    // stub_id derived from worker_name via regex per e2e_targets.py:33-36
    const stubId = encodeURIComponent(stem)
    const res = await fetch(`https://api.beam.cloud/v2/task/${stubId}`, {
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

async function probeRunpod(key: string, name: string): Promise<Status> {
  try {
    const res = await fetch(`https://api.runpod.io/v2/endpoints`, {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(2000),
    })
    if (!res.ok) return "unknown"
    const list = await res.json().catch(() => [])
    const ep = Array.isArray(list) ? list.find((e:any)=> e.name === name) : null
    if (!ep) return "deployed"
    const health = await fetch(`https://api.runpod.io/v2/endpoints/${ep.id}/health`, {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(2000),
    })
    if (health.ok) return "healthy"
    return "unhealthy"
  } catch {
    return "unknown"
  }
}

async function probeModal(tokenId: string, tokenSecret: string, stem: string): Promise<Status> {
  try {
    // Modal has no documented REST health endpoint; fallback to unknown per spec
    return "unknown"
  } catch {
    return "unknown"
  }
}
