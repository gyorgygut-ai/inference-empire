import type { ExecutorContext } from '@nx/devkit';

import executor, { buildCommand } from './validate-deps';

const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: { nodes: {}, dependencies: {} },
  projectsConfigurations: { projects: {}, version: 2 },
  nxJsonConfiguration: {},
};

describe('ValidateDeps Executor', () => {
  it('builds the default command', () => {
    expect(buildCommand('flux2', '3.11')).toBe(
      'export PATH="$(echo "$PATH" | tr \':\' \'\\n\' | grep -v \'Versions/2.7\' | paste -sd: -)" && uv run --locked --python 3.11 python tools/workspace-plugin/src/executors/validate-deps/validate_deps.py flux2 | uv pip compile --python-version 3.11 -'
    );
  });

  it('honors the python version option', () => {
    expect(buildCommand('realtime_voice', '3.10')).toContain('--python-version 3.10 -');
  });

  it('fails without a family', async () => {
    const output = await executor({ family: '' }, context);
    expect(output.success).toBe(false);
  });
});
