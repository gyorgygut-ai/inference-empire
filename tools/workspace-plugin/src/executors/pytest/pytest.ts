import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { PytestExecutorSchema } from './schema';

export function buildCommand(family: string, mode: 'unit' | 'e2e'): string {
  const k = mode === 'e2e' ? 'e2e' : 'not e2e';
  return `uv run --locked pytest apps/${family}/tests/ -k "${k}" -q`;
}

const runExecutor: PromiseExecutor<PytestExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return {
    success: runCommand(
      buildCommand(options.family, options.mode ?? 'unit'),
      context.root
    ),
  };
};

export default runExecutor;
