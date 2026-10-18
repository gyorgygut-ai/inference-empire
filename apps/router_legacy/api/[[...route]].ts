import { getRequestListener } from '@hono/node-server'
import { handle } from '../src/handler.js'
import { envSchema } from '../env.schema.js'

// Vercel mounts this function under /api/*; the router's own routes are /q and /sup.
function stripApiPrefix(request: Request): Request {
  const url = new URL(request.url)
  if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) return request
  url.pathname = url.pathname.slice('/api'.length) || '/'
  return new Request(url, request)
}

export default getRequestListener((request) =>
  handle(
    stripApiPrefix(request),
    envSchema.parse({ ...process.env, PORT: process.env.PORT ?? '3000' }),
  ),
)
