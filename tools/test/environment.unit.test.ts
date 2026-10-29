import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import { afterAll, beforeAll, expect, test } from 'vitest'

const require = createRequire(import.meta.url)
const workspace = resolve(import.meta.dirname, '../..')
const fixture = mkdtempSync(join(tmpdir(), 'nx-env-proof-'))
const nx = join(dirname(require.resolve('nx/package.json')), 'dist/bin/nx.js')
const results: Array<Record<string, Record<string, string>>> = []
const hash = (value: string) => createHash('sha256').update(value).digest('hex')

function write(path: string, contents: string) {
  const destination = join(fixture, path)
  mkdirSync(dirname(destination), { recursive: true })
  writeFileSync(destination, contents)
}

function projectTarget(project: string, target: string, vendor: string) {
  const config = JSON.parse(readFileSync(join(workspace, `apps/${project}/project.json`), 'utf8'))
  const options = config.targets[target].options
  expect(options.command ?? options.commands[0]).toContain(`npx ${vendor}`)
  const rest = { ...options }
  delete rest.commands
  return { executor: config.targets[target].executor, cache: false, options: {
    ...rest, command: `"${process.execPath}" "${join(fixture, 'probe.cjs')}"`,
  } }
}

beforeAll(() => {
  symlinkSync(join(workspace, 'node_modules'), join(fixture, 'node_modules'), 'dir')
  write('package.json', JSON.stringify({ name: 'native-env-proof', private: true }))
  write('nx.json', JSON.stringify({ plugins: [], useInferencePlugins: false }))
  write('tsconfig.base.json', readFileSync(join(workspace, 'tsconfig.base.json'), 'utf8'))
  write('probe.cjs', [
    "const {createHash}=require('node:crypto')",
    "const hash=value=>value?createHash('sha256').update(value).digest('hex'):''",
    "const env=process.env",
    "const output={flux:hash(env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN),tinysd:hash(env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN),auth:hash(env.AUTH_TOKEN||env.ROUTER_AUTH_TOKEN),beam:hash(env.BEAM_TOKEN),project:hash(env.PROBE_PROJECT_SECRET),port:env.ROUTER_FLUX2_PORT,routerUrl:env.ROUTER_URL,workerUrl:env.WORKER_BEAM_URL}",
    "output.args=process.argv.slice(2).join(' ')",
    "require('node:fs').writeFileSync(env.NX_WORKSPACE_ROOT+'/'+env.NX_TASK_TARGET_PROJECT+'-'+env.NX_TASK_TARGET_TARGET+'.json',JSON.stringify(output))",
  ].join('\n'))
  write('tools/generate-auth-token.ts', readFileSync(join(workspace, 'tools/generate-auth-token.ts'), 'utf8'))
  write('tools/get-beam-url.ts', "console.log('https://' + process.argv[2] + '.example.test')\n")
  write('tools/get-cf-worker-url.ts', "console.log('https://' + process.argv[2] + '.example.test')\n")
  write('.env', 'BEAM_TOKEN=fixture-root-beam\nROUTER_FLUX2_PORT=9999\nROUTER_FLUX2_GENERATED_AUTH_TOKEN=stale-flux\nROUTER_TINYSD_GENERATED_AUTH_TOKEN=stale-tinysd\n')
  for (const mode of ['dev', 'deploy']) {write(`config.${mode}`, readFileSync(join(workspace, `config.${mode}`), 'utf8'))}
  write('apps/functions/.env', 'PROBE_PROJECT_SECRET=fixture-router-secret\n')
  write('apps/face-value/.env', 'PROBE_PROJECT_SECRET=fixture-frontend-secret\n')
  write('apps/functions/project.json', JSON.stringify({ name: 'functions', targets: {
    'dev-flux2': projectTarget('functions', 'dev-flux2', 'wrangler dev'),
    'dev-tinysd': projectTarget('functions', 'dev-tinysd', 'wrangler dev'),
    'deploy-flux2': projectTarget('functions', 'deploy-flux2', 'wrangler deploy'),
    'deploy-tinysd': projectTarget('functions', 'deploy-tinysd', 'wrangler deploy'),
  } }))
  write('apps/face-value/project.json', JSON.stringify({ name: 'face-value', targets: {
    dev: projectTarget('face-value', 'dev', 'next dev'), deploy: projectTarget('face-value', 'deploy', 'vercel deploy'),
  } }))
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(NX_|ROUTER_|FACE_VALUE_PORT$|VOICE_CHAT_PORT$|BEAM_TOKEN$|AUTH_TOKEN$|PROBE_)/.test(key)))
  for (const mode of ['dev', 'dev', 'deploy']) {
    execFileSync(join(workspace, 'node_modules/.bin/dotenvx'), ['run', '--overload', '-f', `config.${mode}`, '--', process.execPath, nx, 'run-many', '-t', `${mode}-flux2`, `${mode}-tinysd`, mode, '--parallel=3', '--outputStyle=stream'], {
      cwd: fixture, timeout: 60000, stdio: 'inherit',
      env: { ...env, NX_DAEMON: 'false', NX_NO_CLOUD: 'true', NX_TUI: 'false', NX_INTERACTIVE: 'false' },
    })
    results.push(Object.fromEntries(['functions-dev-flux2', 'functions-dev-tinysd', 'face-value-dev'].map(id => [
      id, JSON.parse(readFileSync(join(fixture, `${id.replace('-dev', `-${mode}`)}.json`), 'utf8')),
    ])))
  }
}, 180000)

afterAll(() => rmSync(fixture, { recursive: true, force: true }))

test('Nx loads root credentials after dotenvx loads only shared config', () => {
  expect(Object.values(results[0]).map(result => result.beam)).toEqual(Array(3).fill(hash('fixture-root-beam')))
})

test('Nx loads each project credential without leaking it to sibling projects', () => {
  expect(results[0]['functions-dev-tinysd'].project).toBe(hash('fixture-router-secret'))
  expect(results[0]['face-value-dev'].project).toBe(hash('fixture-frontend-secret'))
})

test('shared config wins over conflicting root environment values', () => {
  expect(results[0]['functions-dev-flux2'].port).toBe('3000')
  expect(results[0]['functions-dev-flux2'].flux).not.toBe(hash('stale-flux'))
  expect(results[0]['functions-dev-tinysd'].tinysd).not.toBe(hash('stale-tinysd'))
})

test('concurrent router targets receive their own invocation-generated token', () => {
  expect(results[0]['functions-dev-flux2'].auth).toBe(results[0]['functions-dev-flux2'].flux)
  expect(results[0]['functions-dev-tinysd'].auth).toBe(results[0]['functions-dev-tinysd'].tinysd)
  expect(results[0]['functions-dev-flux2'].auth).not.toBe(results[0]['functions-dev-tinysd'].auth)
})

test('frontend and flux2 share one token and the delegated router URL', () => {
  expect(results[0]['face-value-dev'].auth).toBe(results[0]['functions-dev-flux2'].auth)
  expect(results[0]['face-value-dev'].routerUrl).toBe('http://localhost:3000')
})

test('router targets resolve the matching worker URL', () => {
  expect(results[0]['functions-dev-flux2'].workerUrl).toBe('https://workers-flux2.example.test')
  expect(results[0]['functions-dev-tinysd'].workerUrl).toBe('https://workers-tiny_sd.example.test')
})

test('tokens stay consistent across tasks within each invocation', () => {
  for (const run of results) {expect(new Set(Object.values(run).map(result => result.flux)).size).toBe(1)}
  for (const run of results) {expect(new Set(Object.values(run).map(result => result.tinysd)).size).toBe(1)}
})

test('options.args forwards ports with shell environment expansion', () => {
  expect(results[0]['functions-dev-flux2'].args).toContain('--port=3000')
  expect(results[0]['functions-dev-tinysd'].args).toContain('--port=3025')
  expect(results[0]['face-value-dev'].args).toBe('--port=3050')
})

test('both tokens are regenerated between invocations and deployment config works', () => {
  expect(new Set(results.map(run => run['functions-dev-flux2'].flux)).size).toBe(3)
  expect(new Set(results.map(run => run['functions-dev-tinysd'].tinysd)).size).toBe(3)
  expect(results[2]['functions-dev-tinysd'].auth).toBe(results[2]['functions-dev-tinysd'].tinysd)
})

test('deployment frontend receives the matching token and resolved router URL', () => {
  expect(results[2]['face-value-dev'].auth).toBe(results[2]['functions-dev-flux2'].auth)
  expect(results[2]['face-value-dev'].routerUrl).toBe('https://router_flux2.example.test')
})
