import { verifyToken } from "./auth"
import { encodeTaskId, decodeTaskId } from "./task-id"
import { parseQueueBody } from "./contracts"
import { selectProvider } from "./providers/selector"

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    try {
      const ok = await verifyToken(request.headers.get("Authorization"), env.AUTH_TOKEN)
      if (!ok) {
        console.error(JSON.stringify({ message: "unauthorized", path: new URL(request.url).pathname }))
        return Response.json({ error: "Unauthorized" }, { status: 401 })
      }
      const url = new URL(request.url)
      if (request.method === "POST" && url.pathname === "/queue") {
        const body: unknown = await request.json()
        const input = parseQueueBody(body, env.CONTRACT)
        if (input === null) return Response.json({ error: "Bad request" }, { status: 400 })
        console.log(JSON.stringify({ message: "queue", contract: env.CONTRACT }))
        const adapter = selectProvider(env)
        const providerId = await adapter.queue(input)
        ctx.waitUntil(Promise.resolve().then(() => console.log(JSON.stringify({ message: "queued" }))))
        return Response.json({ task_id: encodeTaskId(adapter.name, providerId) }, { status: 202 })
      }
      if (request.method === "GET" && url.pathname.startsWith("/task/")) {
        const raw = decodeURIComponent(url.pathname.slice("/task/".length))
        const decoded = decodeTaskId(raw)
        if (decoded === null) return Response.json({ error: "Not found" }, { status: 404 })
        const adapter = selectProvider(env, decoded.provider)
        const result = await adapter.status(decoded.id)
        return Response.json(result, { status: 200 })
      }
      return Response.json({ error: "Not found" }, { status: 404 })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      console.error(JSON.stringify({ message: "unhandled error", error: message }))
      return Response.json({ error: "Internal server error" }, { status: 500 })
    }
  }
} satisfies ExportedHandler<Env>
