import type { Handler } from "@netlify/functions"
import { createRouter } from "./_shared/router"
import { api as krea2Api } from "@packages/schemas/krea2/schema"
import { readConfig } from "./_shared/config"

const router = createRouter(krea2Api, "/krea2", { readConfig: () => readConfig() })

export const handler: Handler = async (event) => {
  const host = event.headers.host
  const rawUrl = event.rawUrl || `http://${host}${event.path}`
  const req = new Request(rawUrl, {
    method: event.httpMethod,
    headers: Object.fromEntries(Object.entries(event.headers).filter((entry): entry is [string, string] => entry[1] !== undefined)),
    body: event.body
      ? event.isBase64Encoded
        ? Buffer.from(event.body, "base64")
        : event.body
      : undefined,
  })
  const res = await router.fetch(req)
  return {
    statusCode: res.status,
    headers: Object.fromEntries(res.headers.entries()),
    body: await res.text(),
  }
}
