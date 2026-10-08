import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { SandboxE2eExecutorSchema } from './schema';

export function buildCommand(family: string, timeout: number, gpu: string): string {
  return `SANDBOX_TIMEOUT=${timeout} SANDBOX_GPU=${gpu} uv run --locked python apps/${family}/sandbox_e2e.py`;
}

const runExecutor: PromiseExecutor<SandboxE2eExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return {
    success: runCommand(
      buildCommand(options.family, options.timeout ?? 600, options.gpu ?? 'L4'),
      context.root
    ),
  };
};

export default runExecutor;
