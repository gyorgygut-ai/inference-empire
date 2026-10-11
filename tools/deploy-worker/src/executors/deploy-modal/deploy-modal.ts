import { join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import { getProjectRootRel, resolveWorkerFile } from '../resolve-worker';
import { runCommand } from '../run-command';
import { writeDeployEndpoints } from '../write-deploy-endpoints';
import type { DeployModalExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<DeployModalExecutorSchema> = async (
  options,
  context: ExecutorContext
) => {
  if (!options.worker) {
    console.error('[deploy-modal] worker is required');
    return { success: false };
  }
  const projectRootRel = getProjectRootRel(context);
  const cwd = join(context.root, projectRootRel);
  const resolved = resolveWorkerFile(cwd, options.worker);
  if ('error' in resolved) {
    console.error(resolved.error);
    return { success: false };
  }
  const ok = runCommand(`modal deploy ${resolved.file}`, cwd, { PYTHONPATH: context.root });
  if (!ok) return { success: false };
  const appUrl = process.env.APP_URL ?? '';
  const beamUrl = process.env.BEAM_URL ?? appUrl;
  if (!appUrl) {
    console.error('[deploy-modal] APP_URL env required so deploy-endpoints.json can be written');
    return { success: false };
  }
  writeDeployEndpoints(context.root, projectRootRel, {
    producer: 'modal',
    worker: options.worker,
    appUrl,
    beamUrl,
  });
  return { success: true };
};

export default runExecutor;