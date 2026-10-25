import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { VultureExecutorSchema } from './schema';

export function buildCommand(projectRoot: string): string {
  return `uv run --locked --group test vulture ${projectRoot}`;
}

const runExecutor: PromiseExecutor<VultureExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.projectRoot) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.projectRoot), context.root) };
};

export default runExecutor;
