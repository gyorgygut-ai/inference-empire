import { randomBytes } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { GenerateExecutorSchema } from './schema';

export function mintAuthToken(): string {
  return randomBytes(32).toString('base64url');
}

function upsertToken(file: string, key: string, token: string): void {
  mkdirSync(dirname(file), { recursive: true });
  const existing = existsSync(file) ? readFileSync(file, 'utf8') : '';
  const line = `${key}=${token}`;
  const lines = existing.length ? existing.split('\n') : [];
  let replaced = false;
  const next = lines.map((l) => {
    if (l.trim().startsWith(`${key}=`)) {
      replaced = true;
      return line;
    }
    return l;
  });
  if (!replaced) {
    next.push(line);
  }
  let body = next.join('\n');
  if (body.charAt(body.length - 1) !== '\n') {
    body += '\n';
  }
  writeFileSync(file, body);
}

const runExecutor: PromiseExecutor<GenerateExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.key) {
    console.error('[nx-generate-auth-token] key is required');
    return { success: false };
  }
  const token = mintAuthToken();
  if (options.file) {
    const file = resolve(context.root, options.file);
    upsertToken(file, options.key, token);
    console.log(`wrote ${options.key} to ${options.file}`);
  } else {
    console.log(token);
  }
  return { success: true };
};

export default runExecutor;
