import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { delay } from 'node:timers/promises'

const ROOT = process.cwd()
const URL = 'http://127.0.0.1:5042'
const DEV_ENV_FILE = join(ROOT, 'dist/krea2/dev.env')

let server: ChildProcess

beforeAll(async () => {
  server = spawn('npx', ['nx', 'run', 'router:dev-krea2'], {
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

describe('router:dev-krea2', () => {
  test('dist/krea2/dev.env: MODAL_WORKER_URL exists', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/MODAL_WORKER_URL=/)
  })

  test('dist/krea2/dev.env: ROUTER_URL is http://127.0.0.1:5042', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/ROUTER_URL=http:\/\/127\.0\.0\.1:5042/)
  })

  test('dist/krea2/dev.env: ROUTER_AUTH_TOKEN exists', () => {
    const content = readFileSync(DEV_ENV_FILE, 'utf8')
    expect(content).toMatch(/ROUTER_AUTH_TOKEN=/)
  })

  test('apps/router/generated/api-krea2.ts exists', () => {
    expect(existsSync(join(ROOT, 'apps/router/generated/api-krea2.ts'))).toBe(true)
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
      .find(line => line.startsWith('SECRET_AUTH_TOKEN='))!
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
  })

  test('GET /sup with token returns status', async () => {
    const tokenLine = readFileSync(DEV_ENV_FILE, 'utf8')
      .split('\n')
      .find(line => line.startsWith('SECRET_AUTH_TOKEN='))!
    const token = tokenLine.split('=')[1]
    const res = await fetch(`${URL}/sup?id=abc`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']).toContain(body.status)
  })
})