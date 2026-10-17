import type { PromiseExecutor } from '@nx/devkit';
import { runChild } from '../run';
import type { RunNodeServerExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<RunNodeServerExecutorSchema> = async (options, context) => {
  if (!options.command) {
    console.error('[orchestrator:run-node-server] missing required option: command');
    return { success: false };
  }
  return await runChild(options, {
    cwd: context.root ?? process.cwd(),
    continuous: true,
  });
};

export default runExecutor;
