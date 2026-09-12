import { NextRequest } from "next/server"

export async function POST(req: NextRequest, context: { params: Promise<{ model: string }> }) {
  const { model } = await context.params
  const body = await req.json().catch(() => ({}))
  const inputs = body.inputs ?? body

  // Internal proxy: hide provider keys on server, forward to real provider here
  // Stubbed for build; replace with real provider forwarding
  return Response.json({ presigned_url: `https://example.com/${model}/${Date.now()}`, inputs })
}

async function pollTask(proxyUrl: string, model: string, taskId: string, key?: string) {
  const deadline = Date.now() + 3600_000
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${proxyUrl}/workers/${model}/task/${taskId}`, {
        headers: key ? { authorization: `Bearer ${key}` } : {},
        signal: AbortSignal.timeout(10_000),
      })
      const data = await res.json().catch(() => ({}))
      if (data.status === "completed" || data.presigned_url || data.output) return data
      if (data.status === "failed") return data
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 2000))
  }
  return { error: "timeout", task_id: taskId }
}
