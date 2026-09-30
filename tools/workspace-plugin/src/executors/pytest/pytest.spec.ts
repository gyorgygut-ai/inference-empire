import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './pytest';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Pytest Executor', () => {
  it('builds the unit command', () => {
    expect(buildCommand('tiny_sd', 'unit')).toBe(
      'uv run --locked --group test pytest apps/tiny_sd/tests/ -k "not e2e" -q'
    );
  });

  it('builds the e2e command', () => {
    expect(buildCommand('tiny_sd', 'e2e')).toBe(
      'uv run --locked --group test pytest apps/tiny_sd/tests/ -k "e2e" -q'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
