import { readFileSync, writeFileSync } from 'node:fs';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import {
  runGenerate,
  resolveOutputPath,
  upsertDotenvLine,
} from '@inference/nx-generate-auth-token';
import type { ResolveExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<ResolveExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.output) {
    console.error('[nx-distribute-resolved-url] output is required');
    return { success: false };
  }
  const appUrl = process.env.APP_URL ?? '';
  if (!appUrl) {
    console.error('[nx-distribute-resolved-url] APP_URL is not set');
    return { success: false };
  }
  const generated = await runGenerate(
    { key: 'SECRET_AUTH_TOKEN', output: options.output },
    context
  );
  if (!generated.success) {
    return generated;
  }
  const out = resolveOutputPath(context, options.output);
  const existing = readFileSync(out, 'utf8');
  writeFileSync(out, upsertDotenvLine(existing, 'APP_URL', appUrl));
  return { success: true };
};

export default runExecutor;
