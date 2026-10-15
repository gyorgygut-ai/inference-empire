import { ExecutorContext } from '@nx/devkit';

import { RunInjectedCommandExecutorSchema } from './schema';
import executor from './run-injected-command';

const options: RunInjectedCommandExecutorSchema = {
  command: 'echo hello',
  inject: [{ env: 'TEST_VAL', command: 'echo', args: ['hello'] }],
};
const context: ExecutorContext = {
  root: '',
  cwd: process.cwd(),
  isVerbose: false,
  projectGraph: {
    nodes: {},
    dependencies: {},
  },
  projectsConfigurations: {
    projects: {},
    version: 2,
  },
  nxJsonConfiguration: {},
};

describe('RunInjectedCommand Executor', () => {
  it('can run', async () => {
    const output = await executor(options, context);
    expect(output.success).toBe(true);
  });

  it('writes top-level artifact', async () => {
    const out = await executor(
      { command: 'echo https://example.com', inject: [], artifact: '/tmp/nx-inject-artifact-test' },
      context
    );
    expect(out.success).toBe(true);
  });
});