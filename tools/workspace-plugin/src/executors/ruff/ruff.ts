import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { RuffExecutorSchema } from './schema';

export function buildCommand(projectRoot: string): string {
  return `uvx ruff check ${projectRoot} --line-length 100`;
}

const runExecutor: PromiseExecutor<RuffExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.projectRoot) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.projectRoot), context.root) };
};

export default runExecutor;
