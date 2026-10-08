import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { RealE2eExecutorSchema } from './schema';

export function buildCommand(family: string): string {
  return `uv run --locked --group test pytest apps/${family}/tests/ -k "e2e" -q`;
}

const runExecutor: PromiseExecutor<RealE2eExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return {
    success: runCommand(buildCommand(options.family), context.root),
  };
};

export default runExecutor;
