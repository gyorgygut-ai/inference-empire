import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { ValidateDepsExecutorSchema } from './schema';

export function buildCommand(family: string, pythonVersion: string): string {
  return `export PATH="$(echo "$PATH" | tr ':' '\\n' | grep -v 'Versions/2.7' | paste -sd: -)" && uv run --locked --python 3.11 python tools/workspace-plugin/src/executors/validate-deps/validate_deps.py ${family} | uv pip compile --python-version ${pythonVersion} -`;
}

const runExecutor: PromiseExecutor<ValidateDepsExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return {
    success: runCommand(
      buildCommand(options.family, options.python_version ?? '3.11'),
      context.root
    ),
  };
};

export default runExecutor;
