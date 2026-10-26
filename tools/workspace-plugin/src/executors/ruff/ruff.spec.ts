import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './ruff';

const context: ExecutorContext = {
  root: '/ws',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Ruff Executor', () => {
  it('builds the lint command', () => {
    expect(buildCommand('apps/workers/flux2')).toBe('uvx ruff check apps/workers/flux2 --line-length 100');
  });

  it('builds the autofix command', () => {
    expect(buildCommand('apps/workers/flux2', true)).toBe('uvx ruff check apps/workers/flux2 --line-length 100 --fix');
  });

  it('fails without a project root', async () => {
    const output = await executor({ projectRoot: '' }, context);
    expect(output.success).toBe(false);
  });
});
