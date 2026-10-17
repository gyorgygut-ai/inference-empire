import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { runChild } from '../run';
import type { RunCommandExecutorSchema } from './schema';

function isContinuous(context: ExecutorContext): boolean {
  const node = context.projectName ? context.projectGraph?.nodes?.[context.projectName] : undefined;
  const target = context.targetName ? node?.data?.targets?.[context.targetName] : undefined;
  return (target as { continuous?: boolean } | undefined)?.continuous === true;
}

const runExecutor: PromiseExecutor<RunCommandExecutorSchema> = async (options, context) => {
  if (!options.command) {
    console.error('[orchestrator:run-command] missing required option: command');
    return { success: false };
  }
  return await runChild(options, {
    cwd: context.root ?? process.cwd(),
    continuous: isContinuous(context),
  });
};

export default runExecutor;
