import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { delay } from 'node:timers/promises'

const ROOT = process.cwd()
const URL = 'http://127.0.0.1:5040'
const DEV_ENV_FILE = join(ROOT, 'dist/flux2/dev.env')

let server: ChildProcess
let taskId: string

beforeAll(async () => {
  server = spawn('npx', ['nx', 'run', 'router:dev-flux2'], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'ignore'],
  })
  await new Promise<void>((resolve) => {
    server.stdout?.on('data', (d: Buffer) => {
      if (d.toString().includes('listening on')) resolve()
    })
  })
  await delay(2000)
})

afterAll(() => server.kill())

describe('router:dev-flux2', () => {
  test('dist/flux2/dev.env: MODAL_WORKER_URL exists', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/MODAL_WORKER_URL=/)
  })

  test('dist/flux2/dev.env: BEAM_WORKER_URL exists', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/BEAM_WORKER_URL=/)
  })

  test('dist/flux2/dev.env: ROUTER_URL is http://127.0.0.1:5040', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/ROUTER_URL=http:\/\/127\.0\.0\.1:5040/)
  })

  test('dist/flux2/dev.env: ROUTER_AUTH_TOKEN exists', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/ROUTER_AUTH_TOKEN=/)
  })

  test('packages/schemas/flux2/schema.ts exists', () => {
    expect(existsSync(join(ROOT, 'packages/schemas/flux2/schema.ts'))).toBe(true)
  })

  test('dist/flux2/dev.env: MODAL_WORKER_URL can be pinged', async () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    const modalUrlLine = content.split('\n').find(line => line.startsWith('MODAL_WORKER_URL='))!
    const modalUrl = modalUrlLine.split('=')[1]
    const res = await fetch(modalUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('dist/flux2/dev.env: BEAM_WORKER_URL can be pinged', async () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    const beamUrlLine = content.split('\n').find(line => line.startsWith('BEAM_WORKER_URL='))!
    const beamUrl = beamUrlLine.split('=')[1]
    const res = await fetch(beamUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('POST /q without token → 401', async () => {
    const res = await fetch(`${URL}/q`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { prompt: 'test' } }),
    })
    expect(res.status).toBe(401)
  })

  test('GET /sup without token → 401', async () => {
    const res = await fetch(`${URL}/sup?id=abc`)
    expect(res.status).toBe(401)
  })

  test('POST /q with token returns task_id', async () => {
    const tokenLine = readFileSync(DEV_ENV_FILE, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_AUTH_TOKEN='))!
    const token = tokenLine.split('=')[1]
    const res = await fetch(`${URL}/q`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ input: { prompt: 'test' } }),
    })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body).toHaveProperty('task_id')
    expect(typeof body.task_id).toBe('string')
    taskId = body.task_id
  })

  test('GET /sup with token returns status', async () => {
    const res = await fetch(`${URL}/sup?id=${taskId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body).toHaveProperty('status')
    expect(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']).toContain(body.status)
  })
})