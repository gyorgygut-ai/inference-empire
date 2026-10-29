import { parse } from '@dotenvx/dotenvx'
import type { ExecutorContext } from '@nx/devkit'
import runCommands, { type RunCommandsOptions } from 'nx/src/executors/run-commands/run-commands.impl'

export default function executor(options: RunCommandsOptions, context: ExecutorContext) {
  const source = Object.entries(options.env ?? {})
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join('\n')
  const env = parse(source, { processEnv: { ...process.env } as Record<string, string>, overload: true })
  return runCommands({ ...options, env }, context)
}
