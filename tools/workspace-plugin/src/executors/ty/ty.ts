import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { TyExecutorSchema } from './schema';

export function buildCommand(family: string): string {
  return `uv run --locked --group test ty check apps/${family}`;
}

const runExecutor: PromiseExecutor<TyExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.family), context.root) };
};

export default runExecutor;
