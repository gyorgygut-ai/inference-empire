import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { router } from './router';
import type { Env } from './index';

function resolveEnv(): Env {
  const token = process.env.SECRET_AUTH_TOKEN ?? '';
  if (!token) {
    throw new Error('SECRET_AUTH_TOKEN is required');
  }
  return { SECRET_AUTH_TOKEN: token };
}

async function toRequest(req: IncomingMessage): Promise<Request> {
  const host = req.headers.host ?? 'localhost';
  const url = new URL(req.url ?? '/', `http://${host}`);
  const headers = new Headers();
  for (const [k, v] of Object.entries(req.headers)) {
    if (typeof v === 'string') {
      headers.set(k, v);
    } else if (Array.isArray(v)) {
      headers.set(k, v.join(', '));
    }
  }
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(chunk as Buffer);
  }
  const body = chunks.length > 0 ? Buffer.concat(chunks) : undefined;
  return new Request(url.toString(), {
    method: req.method ?? 'GET',
    headers,
    body: body && body.length > 0 ? (body as unknown as BodyInit) : undefined,
  });
}

const env = resolveEnv();

const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
  try {
    const request = await toRequest(req);
    const response = await router.fetch(request, env, undefined);
    res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    const buf = Buffer.from(await response.arrayBuffer());
    res.end(buf);
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: (err as Error).message }));
  }
});

server.listen(0, '127.0.0.1', () => {
  const addr = server.address();
  const port = typeof addr === 'object' && addr !== null ? addr.port : 0;
  console.log(`listening on http://127.0.0.1:${port}`);
});
