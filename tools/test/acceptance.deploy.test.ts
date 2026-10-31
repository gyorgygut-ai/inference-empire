import { expect, test } from 'vitest'
import { resolve } from 'node:path'
import { promisify } from 'node:util'
import { execFile } from 'node:child_process'
import { configSchema } from '../../packages/schemas/config.schema'
import { deploySecretsSchema } from '../../packages/schemas/secrets.schema'
import { deployedUrl, expectImage, generateImage, inferenceTimeout, pingFrontend, pingRouter, pingWorker, queueWithToken } from './acceptance-probes'

const env = { ...configSchema.parse(process.env), ...deploySecretsSchema.parse(process.env) }
const execFileAsync = promisify(execFile)
const workspaceRoot = resolve(process.cwd(), '../..')

async function deployedVoiceTurn() {
  const { stdout: workerUrl } = await execFileAsync(
    'npx', ['tsx', 'tools/get-beam-url.ts', 'workers-voice'],
    { cwd: workspaceRoot, env: process.env, timeout: 30_000 },
  )
  const { stdout } = await execFileAsync(
    'uv', [
      'run', '--locked', 'python', 'tests/probe_webrtc.py',
      '--url', workerUrl.trim(), '--token', env.SECRET_BEAM_TOKEN,
      '--voice', 'GutAI', '--output-dir', '.proof/deploy',
    ],
    {
      cwd: resolve(workspaceRoot, 'apps/workers/voice'),
      env: process.env,
      timeout: 660_000,
      maxBuffer: 1024 * 1024,
    },
  )
  return JSON.parse(stdout) as { output_rms: number; voice_id: string; voice_sha256: string; session_id: string }
}

test('deployed workers-flux2 accepts an authenticated ping', () => pingWorker('workers-flux2', env.SECRET_BEAM_TOKEN))

test('deployed workers-tiny_sd accepts an authenticated ping', () => pingWorker('workers-tiny_sd', env.SECRET_BEAM_TOKEN))

test('deployed flux2 /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('flux2', deployedUrl('cf-worker', 'router_flux2'), env.GENERATED_ROUTER_FLUX2_AUTH_TOKEN)
  await expectImage(url)
})

test('deployed flux2 /q rejects the tinysd token', async () => {
  const response = await queueWithToken(deployedUrl('cf-worker', 'router_flux2'), env.GENERATED_ROUTER_TINYSD_AUTH_TOKEN)
  expect(response.status).toBe(401)
  expect(await response.json()).toEqual({ error: 'Unauthorized' })
})

test('deployed tinysd /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('tinysd', deployedUrl('cf-worker', 'router_tinysd'), env.GENERATED_ROUTER_TINYSD_AUTH_TOKEN)
  await expectImage(url)
})

test('deployed face-value can reach its flux2 router', () => pingRouter(deployedUrl('cf-worker', 'router_flux2'), env.GENERATED_ROUTER_FLUX2_AUTH_TOKEN))

test('deployed face-value serves the app', () => pingFrontend(deployedUrl('vercel', env.SECRET_FACE_VALUE_VERCEL_PROJECT_ID, '--org', env.SECRET_FACE_VALUE_VERCEL_ORG_ID)))

test('deployed workers-voice completes a named-voice WebRTC speech turn', { timeout: 670_000 }, async () => {
  const proof = await deployedVoiceTurn()
  expect(proof.output_rms).toBeGreaterThan(160)
  expect(proof).toMatchObject({ voice_id: 'GutAI', voice_sha256: expect.any(String), session_id: expect.any(String) })
})
