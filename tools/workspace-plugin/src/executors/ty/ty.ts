import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { TyExecutorSchema } from './schema';

export function buildCommand(projectRoot: string): string {
  return `uv run --locked --group test ty check ${projectRoot}`;
}

const runExecutor: PromiseExecutor<TyExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.projectRoot) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.projectRoot), context.root) };
};

export default runExecutor;
