import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { beforeAll, describe, expect, it } from 'vitest';
import { inferWithPolling } from '../../packages/task-queue-client/src/client';
import type {
  AddToQueueResponse,
  Flux2Klein9BInput,
  Flux2Klein9BOutput,
  SupResponse,
} from '../generated/api-flux2';

const ROOT = join(process.cwd(), '..', '..');
const ROUTER_URL = readFileSync(
  join(ROOT, 'dist', 'router-flux2', 'deploy', 'ROUTER_URL'),
  'utf8',
).trim();
const TOKEN = readFileSync(
  join(ROOT, 'dist', 'router-flux2', 'deploy', 'SECRET_AUTH_TOKEN'),
  'utf8',
).trim();

const seenTaskIds: string[] = [];
const recordingFetch = (async (url: unknown, init: unknown) => {
  const res: Response = await fetch(url as string, init as RequestInit);
  if (typeof url === 'string' && url.endsWith('/q') && (init as RequestInit)?.method === 'POST') {
    const body = (await res.clone().json()) as AddToQueueResponse;
    seenTaskIds.push(body.task_id);
  }
  return res;
}) as typeof fetch;

function input(seed: number): Flux2Klein9BInput {
  return {
    prompt: 'busty latina woman, portrait photo, natural light',
    width: 512,
    height: 512,
    num_inference_steps: 4,
    seed,
  };
}

async function proveImage(seed: number): Promise<void> {
  const output = await inferWithPolling<Flux2Klein9BInput, Flux2Klein9BOutput>(
    input(seed),
    { baseUrl: ROUTER_URL, token: TOKEN, pollIntervalMs: 10_000, timeoutMs: 280_000 },
    recordingFetch,
  );
  const taskId = seenTaskIds[seenTaskIds.length - 1] as string;
  expect(Buffer.from(taskId, 'base64').toString()).toMatch(/^modal:fc-/);
  expect(output.artifact.presigned_url).toMatch(/^https:\/\//);
  const image = await fetch(output.artifact.presigned_url);
  expect(image.status).toBe(200);
  expect(image.headers.get('content-type')).toContain('image/png');
  expect((await image.arrayBuffer()).byteLength).toBeGreaterThan(50 * 1024);
  const poll: SupResponse = (await (
    await fetch(`${ROUTER_URL}/sup?id=${encodeURIComponent(taskId)}`, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    })
  ).json()) as SupResponse;
  expect(poll.status).toBe('COMPLETED');
  expect(poll.output?.artifact.presigned_url).toBe(output.artifact.presigned_url);
}

describe('router-flux2:deploy full chain', () => {
  beforeAll(() => {
    expect(ROUTER_URL).toMatch(/^https:\/\//);
    expect(TOKEN.length).toBeGreaterThanOrEqual(32);
  });

  it('rejects unauthenticated and malformed requests', async () => {
    const noAuth = await fetch(`${ROUTER_URL}/q`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { prompt: 'hi' } }),
    });
    expect(noAuth.status).toBe(401);

    const wrong = await fetch(`${ROUTER_URL}/q`, {
      method: 'POST',
      headers: { Authorization: 'Bearer wrong', 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { prompt: 'hi' } }),
    });
    expect(wrong.status).toBe(401);

    const supNoAuth = await fetch(`${ROUTER_URL}/sup?id=x`);
    expect(supNoAuth.status).toBe(401);

    const supNoId = await fetch(`${ROUTER_URL}/sup`, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });
    expect(supNoId.status).toBe(400);

    const unknown = await fetch(`${ROUTER_URL}/nope`, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });
    expect(unknown.status).toBe(404);
  });

  it('serves flux image 1 through POST /q + GET /sup', async () => {
    await proveImage(7);
  });

  it('serves flux image 2 through POST /q + GET /sup', async () => {
    await proveImage(8);
  });
});
