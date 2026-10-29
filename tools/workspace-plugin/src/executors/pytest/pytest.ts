import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { PytestExecutorSchema } from './schema';

export function buildCommand(projectRoot: string, mode: 'unit' | 'e2e' = 'unit'): string {
  const selector = mode === 'e2e' ? 'e2e' : 'not e2e';
  return `PYTHONPATH=${projectRoot} uv run --locked --group test pytest ${projectRoot}/tests/ -k "${selector}" -q`;
}

const runExecutor: PromiseExecutor<PytestExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.projectRoot) {
    return { success: false };
  }
  return {
    success: runCommand(buildCommand(options.projectRoot, options.mode), context.root),
  };
};

export default runExecutor;
