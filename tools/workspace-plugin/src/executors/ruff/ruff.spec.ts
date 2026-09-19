import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './ruff';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Ruff Executor', () => {
  it('builds the lint command', () => {
    expect(buildCommand('tiny_sd')).toBe(
      'uvx ruff check apps/gpu-workers/tiny_sd --line-length 100'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
