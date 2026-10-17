import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { delay } from 'node:timers/promises'

const ROOT = process.cwd()
const FLUX2_DEPLOY_ENV = join(ROOT, 'dist/flux2/deploy.env')

let server: ChildProcess
let taskId: string

beforeAll(async () => {
  server = spawn('npx', ['nx', 'run', 'face-value:deploy'], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'ignore'],
  })
  await new Promise<void>((resolve) => {
    server.stdout?.on('data', (d: Buffer) => {
      if (d.toString().includes('Local:') || d.toString().includes('ready')) resolve()
    })
  })
  await delay(3000)
})

afterAll(() => server.kill())

describe('face-value:deploy', () => {
  test('dist/flux2/deploy.env: MODAL_WORKER_URL exists', () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    expect(content).toMatch(/MODAL_WORKER_URL=/)
  })

  test('dist/flux2/deploy.env: MODAL_WORKER_URL can be pinged', async () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    const modalUrl = content.split('\n').find(line => line.startsWith('MODAL_WORKER_URL='))!.split('=')[1].trim()
    const res = await fetch(modalUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('dist/flux2/deploy.env: BEAM_WORKER_URL exists', () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    expect(content).toMatch(/BEAM_WORKER_URL=/)
  })

  test('dist/flux2/deploy.env: BEAM_WORKER_URL can be pinged', async () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    const beamUrl = content.split('\n').find(line => line.startsWith('BEAM_WORKER_URL='))!.split('=')[1].trim()
    const res = await fetch(beamUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('dist/flux2/deploy.env: ROUTER_URL exists', () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    expect(content).toMatch(/ROUTER_URL=/)
  })

  test('dist/flux2/deploy.env: ROUTER_URL is a deployed pingable url', async () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    const routerUrl = content.split('\n').find(line => line.startsWith('ROUTER_URL='))!.split('=')[1].trim()
    const res = await fetch(routerUrl)
    expect(res.status).toBe(200)
  })

  test('dist/flux2/deploy.env: ROUTER_AUTH_TOKEN exists', () => {
    const content = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    expect(content).toMatch(/ROUTER_AUTH_TOKEN=/)
  })

  test('packages/schemas/flux2/schema.ts exists', () => {
    expect(existsSync(join(ROOT, 'packages/schemas/flux2/schema.ts'))).toBe(true)
  })

  test('POST /q without token → 401', async () => {
    const routerUrlLine = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_URL='))!
    const routerUrl = routerUrlLine.split('=')[1].trim()
    const res = await fetch(`${routerUrl}/q`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { prompt: 'test' } }),
    })
    expect(res.status).toBe(401)
  })

  test('POST /q with token returns task_id', async () => {
    const routerUrlLine = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_URL='))!
    const routerUrl = routerUrlLine.split('=')[1].trim()
    const tokenLine = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_AUTH_TOKEN='))!
    const token = tokenLine.split('=')[1].trim()
    const res = await fetch(`${routerUrl}/q`, {
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
    taskId = body.task_id as string
  })

  test('GET /sup returns status', async () => {
    const routerUrlLine = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_URL='))!
    const routerUrl = routerUrlLine.split('=')[1].trim()
    const tokenLine = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_AUTH_TOKEN='))!
    const token = tokenLine.split('=')[1].trim()
    const res = await fetch(`${routerUrl}/sup?id=${taskId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']).toContain(body.status)
  })

  test('GET FACE_VALUE_URL → 200', async () => {
    const flux2DeployEnv = readFileSync(FLUX2_DEPLOY_ENV, 'utf8')
    const faceValueUrlLine = flux2DeployEnv
      .split('\n')
      .find(line => line.startsWith('FACE_VALUE_URL='))!
    const faceValueUrl = faceValueUrlLine.split('=')[1].trim()
    const res = await fetch(faceValueUrl)
    expect(res.status).toBe(200)
  })
})