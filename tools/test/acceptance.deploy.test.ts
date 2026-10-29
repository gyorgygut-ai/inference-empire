import { expect, test } from 'vitest'
import { envSchema } from '../../env.schema.deploy'
import { deployedUrl, expectImage, generateImage, inferenceTimeout, pingFrontend, pingRouter, pingWorker, queueWithToken } from './acceptance-probes'

const env = envSchema.parse(process.env)

test('deployed workers-flux2 accepts an authenticated ping', () => pingWorker('workers-flux2', env.BEAM_TOKEN))

test('deployed workers-tiny_sd accepts an authenticated ping', () => pingWorker('workers-tiny_sd', env.BEAM_TOKEN))

test('deployed flux2 /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('flux2', deployedUrl('cf-worker', 'router_flux2'), env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN)
  await expectImage(url)
})

test('deployed flux2 /q rejects the tinysd token', async () => {
  const response = await queueWithToken(deployedUrl('cf-worker', 'router_flux2'), env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN)
  expect(response.status).toBe(401)
  expect(await response.json()).toEqual({ error: 'Unauthorized' })
})

test('deployed tinysd /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('tinysd', deployedUrl('cf-worker', 'router_tinysd'), env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN)
  await expectImage(url)
})

test('deployed face-value can reach its flux2 router', () => pingRouter(deployedUrl('cf-worker', 'router_flux2'), env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN))

test('deployed face-value serves the app', () => pingFrontend(deployedUrl('vercel', env.FACE_VALUE_VERCEL_PROJECT_ID, '--org', env.FACE_VALUE_VERCEL_ORG_ID)))
