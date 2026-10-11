import { existsSync, readFileSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { EnforceExecutorSchema } from './schema';

type SafeParseResult =
  | { success: true }
  | { success: false; error: { issues: Array<{ path: unknown[]; message: string }> } };

type EnvSchema = {
  safeParse: (env: unknown) => SafeParseResult;
};

function getProjectRootRel(context: ExecutorContext): string {
  const name = context.projectName ?? '';
  const proj = context.projectsConfigurations?.projects?.[name];
  return proj?.root ?? '';
}

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
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

const runExecutor: PromiseExecutor<EnforceExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.schema) {
    console.error('[nx-enforce-env-variables] schema is required');
    return { success: false };
  }
  const expanded = options.schema
    .replace('{workspaceRoot}', context.root)
    .replace('{projectRoot}', join(context.root, getProjectRootRel(context)));
  const schemaPath = isAbsolute(expanded) ? expanded : join(context.root, expanded);
  let mod: unknown;
  try {
    mod = require(schemaPath);
  } catch {
    console.error(`[nx-enforce-env-variables] cannot import ${schemaPath}`);
    return { success: false };
  }
  const record = mod as Record<string, unknown>;
  const candidate = record['envSchema'] ?? record['default'];
  if (
    candidate === null ||
    typeof candidate !== 'object' ||
    typeof (candidate as EnvSchema).safeParse !== 'function'
  ) {
    console.error(`[nx-enforce-env-variables] ${schemaPath} must export envSchema`);
    return { success: false };
  }
  let env: unknown = process.env;
  if (options.file) {
    const expandedFile = options.file
      .replace('{workspaceRoot}', context.root)
      .replace('{projectRoot}', join(context.root, getProjectRootRel(context)));
    const filePath = isAbsolute(expandedFile) ? expandedFile : join(context.root, expandedFile);
    if (!existsSync(filePath)) {
      console.error(`[nx-enforce-env-variables] file not found: ${filePath}`);
      return { success: false };
    }
    env = parseDotenv(readFileSync(filePath, 'utf8'));
  }
  const result = (candidate as EnvSchema).safeParse(env);
  if (!result.success) {
    for (const issue of result.error.issues) {
      console.error(`[nx-enforce-env-variables] ${issue.path.join('.')}: ${issue.message}`);
    }
    return { success: false };
  }
  return { success: true };
};

export default runExecutor;
