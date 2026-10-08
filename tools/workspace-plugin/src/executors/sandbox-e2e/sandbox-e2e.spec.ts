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
      'SANDBOX_TIMEOUT=600 SANDBOX_GPU=L4 uv run --locked python tools/workspace-plugin/src/executors/sandbox-e2e/sandbox_boot.py realtime_voice -- pytest apps/realtime_voice/tests/ -k "e2e" -q --ignore-glob="apps/realtime_voice/tests/*flash*" --ignore-glob="apps/realtime_voice/tests/*beam*"'
    );
  });

  it('honors timeout and gpu options', () => {
    expect(buildCommand('realtime_voice', 300, 'RTX4090')).toBe(
      'SANDBOX_TIMEOUT=300 SANDBOX_GPU=RTX4090 uv run --locked python tools/workspace-plugin/src/executors/sandbox-e2e/sandbox_boot.py realtime_voice -- pytest apps/realtime_voice/tests/ -k "e2e" -q --ignore-glob="apps/realtime_voice/tests/*flash*" --ignore-glob="apps/realtime_voice/tests/*beam*"'
    );
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
