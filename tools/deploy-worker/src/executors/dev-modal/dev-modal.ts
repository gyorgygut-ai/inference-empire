import { join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { getProjectRootRel, resolveWorkerFile } from '../resolve-worker';
import { runCommand } from '../run-command';
import type { DevModalExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<DevModalExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.worker) {
    return { success: false };
  }
  const projectRootRel = getProjectRootRel(context);
  const cwd = join(context.root, projectRootRel);
  const resolved = resolveWorkerFile(cwd, options.worker);
  if ('error' in resolved) {
    console.error(resolved.error);
    return { success: false };
  }
  return {
    success: runCommand(`modal serve ${resolved.file}`, cwd, { PYTHONPATH: context.root }),
  };
};

export default runExecutor;
