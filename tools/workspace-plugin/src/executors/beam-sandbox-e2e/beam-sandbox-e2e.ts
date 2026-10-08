import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { BeamSandboxE2eExecutorSchema } from './schema';

export function buildCommand(family: string, timeout: number, gpu: string): string {
  return `SANDBOX_TIMEOUT=${timeout} SANDBOX_GPU=${gpu} uv run --locked python tools/workspace-plugin/src/executors/beam-sandbox-e2e/beam_sandbox_boot.py ${family} -- pytest apps/${family}/tests/ -k "e2e" -q --ignore-glob="apps/${family}/tests/*flash*" --ignore-glob="apps/${family}/tests/*modal*"`;
}

const runExecutor: PromiseExecutor<BeamSandboxE2eExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.family) {
    return { success: false };
  }
  return {
    success: runCommand(
      buildCommand(options.family, options.timeout ?? 600, options.gpu ?? 'RTX4090'),
      context.root
    ),
  };
};

export default runExecutor;
