import { join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { getProjectRootRel, resolveWorkerFile } from '../resolve-worker';
import { runCommand } from '../run-command';
import type { DevBeamExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<DevBeamExecutorSchema> = async (
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
  const entrypoint = options.entrypoint ?? 'dispatch';
  return {
    success: runCommand(`beam serve ${resolved.file}:${entrypoint}`, cwd, { PYTHONPATH: context.root }),
  };
};

export default runExecutor;
