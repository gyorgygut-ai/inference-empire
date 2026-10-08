import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './sandbox-e2e';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('SandboxE2e Executor', () => {
  it('builds the default command', () => {
    expect(buildCommand('realtime_voice', 600, 'L4')).toBe(
      'SANDBOX_TIMEOUT=600 SANDBOX_GPU=L4 uv run --locked python apps/realtime_voice/sandbox_e2e.py'
    );
  });

  it('honors timeout and gpu options', () => {
    expect(buildCommand('realtime_voice', 300, 'RTX4090')).toBe(
      'SANDBOX_TIMEOUT=300 SANDBOX_GPU=RTX4090 uv run --locked python apps/realtime_voice/sandbox_e2e.py'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
