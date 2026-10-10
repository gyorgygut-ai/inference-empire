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
  const result = (candidate as EnvSchema).safeParse(process.env);
  if (!result.success) {
    for (const issue of result.error.issues) {
      console.error(`[nx-enforce-env-variables] ${issue.path.join('.')}: ${issue.message}`);
    }
    return { success: false };
  }
  return { success: true };
};

export default runExecutor;
