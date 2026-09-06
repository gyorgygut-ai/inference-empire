import { NextRequest } from "next/server"

export async function POST(req: NextRequest, context: { params: Promise<{ model: string }> }) {
  const { model } = await context.params
  const body = await req.json().catch(() => ({}))
  const inputs = body.inputs ?? body

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

  return Response.json({ presigned_url: `https://example.com/${model}/${Date.now()}`, inputs, _stub: true })
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
