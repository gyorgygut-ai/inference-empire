import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import { randomBytes } from 'node:crypto';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { GenerateExecutorSchema } from './schema';

export function mintAuthToken(): string {
  return randomBytes(32).toString('base64url');
}

function getProjectRootRel(context: ExecutorContext): string {
  const name = context.projectName ?? '';
  const proj = context.projectsConfigurations?.projects?.[name];
  return proj?.root ?? '';
}

export function resolveOutputPath(context: ExecutorContext, output: string): string {
  const expanded = output
    .replace('{workspaceRoot}', context.root)
    .replace('{projectRoot}', join(context.root, getProjectRootRel(context)));
  return isAbsolute(expanded) ? expanded : join(context.root, expanded);
}

export function upsertDotenvLine(content: string, key: string, value: string): string {
  const lines = content.length > 0 ? content.split('\n') : [];
  let found = false;
  const next = lines.map((line) => {
    if (line.trim().startsWith(`${key}=`)) {
      found = true;
      return `${key}=${value}`;
    }
    return line;
  });
  if (!found) {
    next.push(`${key}=${value}`);
  }
  const body = next.join('\n');
  return body.endsWith('\n') ? body : `${body}\n`;
}

const runExecutor: PromiseExecutor<GenerateExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.key) {
    console.error('[nx-generate-auth-token] key is required');
    return { success: false };
  }
  if (!options.output) {
    console.error('[nx-generate-auth-token] output is required');
    return { success: false };
  }
  const out = resolveOutputPath(context, options.output);
  mkdirSync(dirname(out), { recursive: true });
  const existing = existsSync(out) ? readFileSync(out, 'utf8') : '';
  writeFileSync(out, upsertDotenvLine(existing, options.key, mintAuthToken()));
  return { success: true };
};

export default runExecutor;
