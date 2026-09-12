import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { RuffExecutorSchema } from './schema';

export function buildCommand(family: string): string {
  return `uvx ruff check workers/${family} --line-length 100`;
}

const runExecutor: PromiseExecutor<RuffExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return { success: runCommand(buildCommand(options.family), context.root) };
};

export default runExecutor;
