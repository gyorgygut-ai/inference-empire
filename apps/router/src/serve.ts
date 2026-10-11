import { existsSync, readFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { router } from './router';
import type { Env } from './index';

function parseDotenv(content: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.length === 0 || trimmed.startsWith('#')) {
      continue;
    }
    const eq = trimmed.indexOf('=');
    if (eq === -1) {
      continue;
    }
    out[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return out;
}

function loadEnvFile(path: string): void {
  if (!existsSync(path)) {
    return;
  }
  const values = parseDotenv(readFileSync(path, 'utf8'));
  for (const [k, v] of Object.entries(values)) {
    if ((process.env[k] ?? '') === '') {
      process.env[k] = v;
    }
  }
}

function resolveEnv(): Env {
  return {
    SECRET_AUTH_TOKEN: process.env.SECRET_AUTH_TOKEN ?? '',
    ROUTER_FAMILY: process.env.ROUTER_FAMILY ?? '',
    BEAM_URL: process.env.BEAM_URL ?? '',
    BEAM_TASK_API: process.env.BEAM_TASK_API ?? '',
    FLASH_URL: process.env.FLASH_URL ?? '',
    FLASH_ENDPOINT: process.env.FLASH_ENDPOINT ?? '',
  };
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

const flavor = process.argv[2] ?? 'flux2';
const port = Number(process.argv[3] ?? (flavor === 'krea2' ? '4202' : '4201'));
const envFile = process.argv[4] ?? `apps/router/dist/router-${flavor}/dev.env`;

loadEnvFile(envFile);
if (!process.env.ROUTER_FAMILY) {
  process.env.ROUTER_FAMILY = flavor;
}

const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
  try {
    const request = await toRequest(req);
    const response = await router.fetch(request, resolveEnv(), undefined);
    res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    const buf = Buffer.from(await response.arrayBuffer());
    res.end(buf);
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: (err as Error).message }));
  }
});

server.listen(port, () => {
  console.log(`[router-${flavor}] listening on :${port} (env: ${envFile})`);
});
