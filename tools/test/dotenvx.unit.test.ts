import { afterEach, expect, test, vi } from 'vitest'
import type { ExecutorContext } from '@nx/devkit'
import runCommands from 'nx/src/executors/run-commands/run-commands.impl'
import executor from '../dotenvx/src/run-commands'

vi.mock('nx/src/executors/run-commands/run-commands.impl', () => ({ default: vi.fn(() => Promise.resolve({ success: true })) }))
const context = { root: process.cwd() } as ExecutorContext
afterEach(() => { vi.clearAllMocks(); vi.unstubAllEnvs() })

test('expands environment references, overrides and cross-key references without mutating inputs', async () => {
  vi.stubEnv('DOTENVX_PROBE', 'inherited')
  const options = { command: 'echo', args: '$DOTENVX_PROBE', env: { DOTENVX_PROBE: 'override', COPY: '${DOTENVX_PROBE}' } }
  await executor(options, context)
  expect(runCommands).toHaveBeenCalledWith({ ...options, env: { DOTENVX_PROBE: 'override', COPY: 'override' } }, context)
  expect(process.env.DOTENVX_PROBE).toBe('inherited')
  expect(options.env.COPY).toBe('${DOTENVX_PROBE}')
})

test('expands inherited values and command substitutions with dotenvx', async () => {
  vi.stubEnv('DOTENVX_PROBE', 'inherited')
  await executor({ command: 'echo', env: { COPY: '${DOTENVX_PROBE}', GENERATED: '$(printf generated)' } }, context)
  expect(runCommands).toHaveBeenCalledWith({ command: 'echo', env: { COPY: 'inherited', GENERATED: 'generated' } }, context)
})

test('preserves command options, original context and the delegated result', async () => {
  const options = { commands: ['echo one', 'echo two'], parallel: false, args: '--flag', cwd: 'tools', readyWhen: 'ready' }
  const result = executor(options, context)
  expect(runCommands).toHaveBeenCalledWith({ ...options, env: {} }, context)
  expect(result).toBe(vi.mocked(runCommands).mock.results[0].value)
  await result
})

test('keeps concurrent invocations isolated', async () => {
  await Promise.all(['first', 'second'].map(value => executor({ command: 'echo', env: { DOTENVX_ISOLATED: value, COPY: '${DOTENVX_ISOLATED}' } }, context)))
  expect(vi.mocked(runCommands).mock.calls.map(([options]) => options.env?.COPY)).toEqual(['first', 'second'])
  expect(process.env.DOTENVX_ISOLATED).toBeUndefined()
})
