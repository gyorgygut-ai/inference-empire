import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { VultureExecutorSchema } from './schema';

export function buildCommand(family: string): string {
  return `uv run --locked --group test vulture apps/${family}`;
}

const runExecutor: PromiseExecutor<VultureExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.family), context.root) };
};

export default runExecutor;
