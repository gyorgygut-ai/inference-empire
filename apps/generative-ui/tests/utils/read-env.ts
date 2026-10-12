import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export function readEnv(relPath: string): Record<string, string> {
  const ws = join(__dirname, '../../../..');
  const p = join(ws, relPath);
  if (!existsSync(p)) {
    throw new Error(`missing artifact: ${relPath}`);
  }
  const out: Record<string, string> = {};
  for (const line of readFileSync(p, 'utf8').split('\n')) {
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

export async function waitForWorker(url: string, timeoutMs = 30000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${url}/sup`, {
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(5000)
      });
      if (res.ok) {
        return;
      }
    } catch (_err) {
      // ignore - keep trying
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`Worker at ${url} did not become healthy within ${timeoutMs}ms`);
}

export async function fetchWithTimeout(
  input: RequestInfo,
  init?: RequestInit
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}
