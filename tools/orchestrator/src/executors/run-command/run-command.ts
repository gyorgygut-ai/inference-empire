import { chmodSync, existsSync, mkdirSync, renameSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import type { PromiseExecutor } from '@nx/devkit'
import { runCommands } from 'nx/src/executors/run-commands/run-commands.impl'
import { lock } from 'proper-lockfile'
import type { ContractModule, RunCommandExecutorSchema } from './schema'

const require = createRequire(resolve(process.cwd(), 'package.json'))
const requireContract = (path: string): unknown => require(path)

type ContractEntry = {
  name: string;
  module: ContractModule;
  resolvers: Record<string, string>;
  schema: { parse(value: unknown): Record<string, string> };
}

const interpolateOptions = (template: string, options: Record<string, unknown>): string =>
  template.replace(/\{options\.([^}]+)\}/g, (_m, key) => {
    const value = options[key]
    if (value === undefined) {throw new Error(`Unresolved placeholder: {options.${key}}`)}
    return String(value)
  })

const runResolver = (command: string, root: string, options: Record<string, unknown>): string => {
  const resolved = interpolateOptions(command, options)
  const executable = /^\S+\.tsx?(?:\s|$)/.test(resolved) ? `npx tsx ${resolved}` : resolved
  const result = spawnSync(executable, { shell: true, cwd: root, encoding: 'utf8', env: { ...process.env, NO_COLOR: '1' } })
  if (result.error) {throw new Error(`Resolver failed to start: ${result.error.message}`)}
  if (result.status !== 0) {throw new Error(`Resolver exited ${result.status}: ${result.stderr?.trim()}`)}
  const output = result.stdout.trim()
  if (!output) {throw new Error('Resolver produced no output')}
  return output
}

const loadDeclaredContracts = (root: string, declaredPaths: readonly string[]): ContractEntry[] =>
  declaredPaths.map((relPath) => {
      const fullPath = resolve(root, relPath.replace(/^\{workspaceRoot\}\//, ''))
      if (!existsSync(fullPath)) {throw new Error(`Declared contract not found: ${relPath}`)}
      const module = requireContract(fullPath) as Record<string, unknown>
      const declaration = Object.entries(module).find(
        (entry): entry is [string, ContractModule] =>
          typeof entry[1] === 'object' && entry[1] !== null && Array.isArray((entry[1] as ContractModule).keys) && typeof (entry[1] as ContractModule).envFilePath === 'string',
      )
      if (!declaration) {throw new Error(`No contract declaration in ${relPath}`)}
      const [name, contract] = declaration
      const resolvers = module[name.replace(/Contract$/, 'Resolvers')] ?? contract.resolvers
      if (!resolvers || typeof resolvers !== 'object') {throw new Error(`No contract resolvers in ${relPath}`)}
      const schema = Object.values(module).find(
        (value): value is ContractEntry['schema'] =>
          typeof value === 'object' && value !== null && 'parse' in value && typeof value.parse === 'function',
      )
      if (!schema) {throw new Error(`No contract schema in ${relPath}`)}
      return { name, module: contract, resolvers: resolvers as Record<string, string>, schema }
    })

const resolveValues = (entry: ContractEntry, root: string, options: Record<string, unknown>): Record<string, string> =>
  entry.schema.parse(Object.fromEntries(
    entry.module.keys.map((key) => {
      const resolver = entry.resolvers[key]
      if (!resolver) {throw new Error(`Contract "${entry.name}" missing resolver for "${key}"`)}
      return [key, runResolver(resolver, root, options)]
    }),
  ))

const resolveEnvOptions = (options: Record<string, unknown>): Record<string, unknown> =>
  Object.fromEntries(
    Object.entries(options).map(([key, value]) => [
      key,
      typeof value === 'string' && value.startsWith('env.')
        ? process.env[value.slice(4)]
        : value,
    ]),
  )

const runExecutor: PromiseExecutor<RunCommandExecutorSchema> = async (options, context) => {
  const root = context.root
  const targetOptions = resolveEnvOptions({ ...(context.target?.options ?? {}), ...options })
  const declaredPaths = (context.target?.inputs ?? []).filter((input): input is string => typeof input === 'string' && input.endsWith('.contract.ts'))
  const contracts = loadDeclaredContracts(root, declaredPaths)

  const inherited: NodeJS.ProcessEnv = { ...process.env }
  for (const entry of contracts) {
    const envFile = resolve(root, entry.module.envFilePath)
    mkdirSync(dirname(envFile), { recursive: true })
    const release = await lock(envFile, {
      realpath: false,
      stale: 120_000,
      retries: { retries: 100, minTimeout: 100, maxTimeout: 500 },
    })
    try {
      const values = resolveValues(entry, root, targetOptions)
      const temporaryFile = `${envFile}.${process.pid}.tmp`
      writeFileSync(temporaryFile, `${Object.entries(values).map(([key, value]) => `${key}=${JSON.stringify(value)}`).join('\n')}\n`, { mode: 0o600 })
      chmodSync(temporaryFile, 0o600)
      renameSync(temporaryFile, envFile)
      Object.assign(inherited, values)
    } finally {
      await release()
    }
  }
  Object.assign(inherited, targetOptions.env ?? {})

  if (typeof targetOptions.command !== 'string' || !targetOptions.command) {throw new Error('run-command requires a command')}
  const command = interpolateOptions(targetOptions.command, targetOptions)
  const args = typeof targetOptions.args === 'string' ? interpolateOptions(targetOptions.args, targetOptions) : ''
  const cwd = typeof targetOptions.cwd === 'string' ? resolve(root, targetOptions.cwd.replace('{workspaceRoot}', root)) : root

  const runningTask = await runCommands(
    {
      command: [command, args].filter(Boolean).join(' '),
      cwd,
      env: Object.fromEntries(Object.entries(inherited).filter((e): e is [string, string] => e[1] !== undefined)),
      streamOutput: true,
      __unparsed__: [],
    },
    context,
  )
  const { code } = await runningTask.getResults()
  return { success: code === 0 }
}

export default runExecutor
