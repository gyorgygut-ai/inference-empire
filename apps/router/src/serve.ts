import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadModel } from './models/index.js';
import { envSchema } from '../env.schema.js';

const appRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
for (const f of ['.env.local', '.env']) {
  const path = join(appRoot, f);
  if (existsSync(path)) process.loadEnvFile(path);
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

async function main(): Promise<void> {
  const env = envSchema.parse(process.env);
  const { router, model } = await loadModel();

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

  server.listen(env.PORT, '127.0.0.1', () => {
    const entries: Array<[string, string | undefined]> = [
      ['modal', env.MODAL_WORKER_URL],
      ['beam', env.BEAM_WORKER_URL],
      ['flash', env.FLASH_WORKER_URL],
    ];
    const loaded = entries
      .filter(([, url]) => url !== undefined)
      .map(([name, url]) => `${name}=${url}`)
      .join(' ');
    console.log(`[router-${model}] listening on http://127.0.0.1:${env.PORT}${loaded ? ` ${loaded}` : ''}`);
  });
}

void main();
