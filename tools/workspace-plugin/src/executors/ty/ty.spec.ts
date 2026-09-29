import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './ty';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Ty Executor', () => {
  it('builds the typecheck command', () => {
    expect(buildCommand('tiny_sd')).toBe('uvx ty check apps/tiny_sd');
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
