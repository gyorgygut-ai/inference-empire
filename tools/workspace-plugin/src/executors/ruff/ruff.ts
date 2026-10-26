import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { RuffExecutorSchema } from './schema';

export function buildCommand(projectRoot: string, fix = false): string {
  return `uvx ruff check ${projectRoot} --line-length 100${fix ? ' --fix' : ''}`;
}

const runExecutor: PromiseExecutor<RuffExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.projectRoot) {
    return { success: false };
  }
  return {
    success: runCommand(buildCommand(options.projectRoot, options.fix), context.root),
  };
};

export default runExecutor;
