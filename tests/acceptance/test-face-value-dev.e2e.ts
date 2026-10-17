import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { delay } from 'node:timers/promises'

const ROOT = process.cwd()
const FLUX2_DEV_ENV = join(ROOT, 'dist/flux2/dev.env')

let server: ChildProcess

beforeAll(async () => {
  server = spawn('npx', ['nx', 'run', 'face-value:dev'], {
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

describe('face-value:dev', () => {
  test('dist/flux2/dev.env: MODAL_WORKER_URL exists', () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    expect(content).toMatch(/MODAL_WORKER_URL=/)
  })

  test('dist/flux2/dev.env: MODAL_WORKER_URL can be pinged', async () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    const modalUrl = content.split('\n').find(line => line.startsWith('MODAL_WORKER_URL='))!.split('=')[1].trim()
    const res = await fetch(modalUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('dist/flux2/dev.env: BEAM_WORKER_URL exists', () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    expect(content).toMatch(/BEAM_WORKER_URL=/)
  })

  test('dist/flux2/dev.env: BEAM_WORKER_URL can be pinged', async () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    const beamUrl = content.split('\n').find(line => line.startsWith('BEAM_WORKER_URL='))!.split('=')[1].trim()
    const res = await fetch(beamUrl, { method: 'GET' })
    expect([200, 404, 503]).toContain(res.status)
  })

  test('dist/flux2/dev.env: ROUTER_URL is http://127.0.0.1:5040', () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    expect(content).toMatch(/ROUTER_URL=http:\/\/127\.0\.0\.1:5040/)
  })

  test('dist/flux2/dev.env: ROUTER_AUTH_TOKEN exists', () => {
    const content = readFileSync(FLUX2_DEV_ENV, 'utf8')
    expect(content).toMatch(/ROUTER_AUTH_TOKEN=/)
  })

  test('packages/schemas/flux2/schema.ts exists', () => {
    expect(existsSync(join(ROOT, 'packages/schemas/flux2/schema.ts'))).toBe(true)
  })

  test('GET / returns 200', async () => {
    const res = await fetch('http://localhost:3000')
    expect(res.status).toBe(200)
  })

  test('ROUTER_AUTH_TOKEN not reachable from browser bundle', () => {
    const tokenLine = readFileSync(FLUX2_DEV_ENV, 'utf8')
      .split('\n')
      .find(line => line.startsWith('ROUTER_AUTH_TOKEN='))!
    const token = tokenLine.split('=')[1].trim()

    const nextStatic = join(ROOT, 'apps/face-value/.next/static')
    let bundleContent = ''
    if (existsSync(nextStatic)) {
      const files = require('node:fs').readdirSync(nextStatic)
      for (const file of files) {
        if (file.endsWith('.js') || file.endsWith('.css')) {
          try {
            const content = readFileSync(join(nextStatic, file), 'utf8')
            bundleContent += content
          } catch (e) {
            // ignore read errors
          }
        }
      }
    }
    expect(bundleContent).not.toContain(token)
  })
})