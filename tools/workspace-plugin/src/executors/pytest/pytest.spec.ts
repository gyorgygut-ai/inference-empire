import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './pytest';

const context: ExecutorContext = {
  root: '/ws',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Pytest Executor', () => {
  it('builds the unit command', () => {
    expect(buildCommand('apps/workers/flux2')).toBe(
      'PYTHONPATH=apps/workers/flux2 uv run --locked --group test pytest apps/workers/flux2/tests/ -k "not e2e" -q'
    );
  });

  it('builds the e2e command', () => {
    expect(buildCommand('apps/workers/flux2', 'e2e')).toBe(
      'PYTHONPATH=apps/workers/flux2 uv run --locked --group test pytest apps/workers/flux2/tests/ -k "e2e" -q'
    );
  });

  it('fails without a project root', async () => {
    const output = await executor({ projectRoot: '' }, context);
    expect(output.success).toBe(false);
  });
});
