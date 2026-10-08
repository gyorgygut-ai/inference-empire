import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './beam-sandbox-e2e';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('BeamSandboxE2e Executor', () => {
  it('builds the default command', () => {
    expect(buildCommand('tiny_sd', 600, 'L4')).toBe(
      'SANDBOX_TIMEOUT=600 SANDBOX_GPU=L4 uv run --locked python tools/workspace-plugin/src/executors/beam-sandbox-e2e/beam_sandbox_boot.py tiny_sd -- pytest apps/tiny_sd/tests/ -k "e2e" -q --ignore-glob="apps/tiny_sd/tests/*flash*" --ignore-glob="apps/tiny_sd/tests/*modal*"'
    );
  });

  it('honors timeout and gpu options', () => {
    expect(buildCommand('tiny_sd', 300, 'RTX4090')).toBe(
      'SANDBOX_TIMEOUT=300 SANDBOX_GPU=RTX4090 uv run --locked python tools/workspace-plugin/src/executors/beam-sandbox-e2e/beam_sandbox_boot.py tiny_sd -- pytest apps/tiny_sd/tests/ -k "e2e" -q --ignore-glob="apps/tiny_sd/tests/*flash*" --ignore-glob="apps/tiny_sd/tests/*modal*"'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
