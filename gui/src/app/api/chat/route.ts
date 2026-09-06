import { NextRequest } from "next/server"

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const model = body.model as string | undefined
  const inputs = (body.inputs ?? body) as Record<string, unknown>

  if (!model) return Response.json({ error: "missing model" }, { status: 400 })

  const proxyUrl = process.env.PROXY_URL
  const proxyKey = process.env.PROXY_KEY

  if (proxyUrl) {
    try {
      const res = await fetch(`${proxyUrl}/workers/${model}`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(proxyKey ? { authorization: `Bearer ${proxyKey}` } : {}),
        },
        body: JSON.stringify(inputs),
        signal: AbortSignal.timeout(3600_000),
      })
      const data = await res.json().catch(() => ({}))
      if (data.task_id) {
        const result = await pollTask(proxyUrl, model, data.task_id, proxyKey)
        return Response.json(result)
      }
      return Response.json(data, { status: res.status })
    } catch (e) {
      return Response.json({ error: String(e), inputs }, { status: 502 })
    }
  }

  if (model === "small_vision") {
    return Response.json({
      classification: "mock",
      subjects: ["mock"],
      description: `mock vision result for ${String(inputs.image_base64 ?? "").slice(0, 20)}`,
      _stub: true,
    })
  }

  return Response.json({ presigned_url: `https://example.com/${model}/${Date.now()}`, _stub: true })
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
