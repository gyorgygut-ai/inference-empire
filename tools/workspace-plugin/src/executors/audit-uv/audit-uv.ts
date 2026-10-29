import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runCommand } from '../run-command';
import type { AuditUvExecutorSchema } from './schema';

export function buildCommand(): string {
  return 'uv pip check';
}

const runExecutor: PromiseExecutor<AuditUvExecutorSchema> = async (
  _options,
  context: ExecutorContext
) => (
  { success: runCommand(buildCommand(), context.root) }
);

export default runExecutor;
