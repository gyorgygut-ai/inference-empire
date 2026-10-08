import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './real-e2e';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('RealE2e Executor', () => {
  it('builds the default command', () => {
    expect(buildCommand('flux2')).toBe(
      'uv run --locked --group test pytest apps/flux2/tests/ -k "e2e" -q'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
