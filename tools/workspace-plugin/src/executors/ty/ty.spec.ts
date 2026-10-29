import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './ty';

const context: ExecutorContext = {
  root: '/ws',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('Ty Executor', () => {
  it('builds the typecheck command', () => {
    expect(buildCommand('apps/workers/flux2')).toBe(
      'uv run --locked --group test ty check apps/workers/flux2'
    );
  });

  it('fails without a project root', async () => {
    const output = await executor({ projectRoot: '' }, context);
    expect(output.success).toBe(false);
  });
});
