import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { delay } from 'node:timers/promises'

const ROOT = process.cwd()

let flux2: ChildProcess
let krea2: ChildProcess

beforeAll(async () => {
  flux2 = spawn('npx', ['nx', 'run', 'router:dev-flux2'], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'ignore'],
  })
  krea2 = spawn('npx', ['nx', 'run', 'router:dev-krea2'], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'ignore'],
  })
  await Promise.all([
    new Promise<void>((r) => flux2.stdout?.on('data', (d: Buffer) => { if (d.toString().includes('listening on')) r() })),
    new Promise<void>((r) => krea2.stdout?.on('data', (d: Buffer) => { if (d.toString().includes('listening on')) r() })),
  ])
  await delay(3000)
})

afterAll(() => { flux2.kill(); krea2.kill() })

describe('router:dev-flux2 + router:dev-krea2 (parallel)', () => {
  test('both listen simultaneously', async () => {
    const [r1, r2] = await Promise.all([
      fetch('http://127.0.0.1:5040/sup?id=x'),
      fetch('http://127.0.0.1:5042/sup?id=x'),
    ])
    expect(r1.status).toBe(401)
    expect(r2.status).toBe(401)
  })

  test('dist/flux2/dev.env: ROUTER_URL is http://127.0.0.1:5040', () => {
    const content = readFileSync(join(ROOT, 'dist/flux2/dev.env'), 'utf8')
    expect(content).toMatch(/ROUTER_URL=http:\/\/127\.0\.0\.1:5040/)
  })

  test('dist/krea2/dev.env: ROUTER_URL is http://127.0.0.1:5042', () => {
    const content = readFileSync(join(ROOT, 'dist/krea2/dev.env'), 'utf8')
    expect(content).toMatch(/ROUTER_URL=http:\/\/127\.0\.0\.1:5042/)
  })

  test('dist files written independently', () => {
    const flux2Port = readFileSync(join(ROOT, 'dist/router-flux2/dev/PORT'), 'utf8').trim()
    const krea2Port = readFileSync(join(ROOT, 'dist/router-krea2/dev/PORT'), 'utf8').trim()
    expect(flux2Port).toBe('5040')
    expect(krea2Port).toBe('5042')
    expect(flux2Port).not.toBe(krea2Port)
  })
})