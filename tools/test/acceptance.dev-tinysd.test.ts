import { expect, test } from 'vitest'
import { configSchema } from '../../packages/schemas/config.schema'
import { devSecretsSchema } from '../../packages/schemas/secrets.schema'
import { expectImage, generateImage, inferenceTimeout, pingWorker, queueWithToken } from './acceptance-probes'

const env = { ...configSchema.parse(process.env), ...devSecretsSchema.parse(process.env) }
const routerUrl = `http://127.0.0.1:${env.DEV_ROUTER_TINYSD_PORT}`

test('worker-tiny_sd accepts an authenticated ping', () => pingWorker('worker-tiny_sd', env.SECRET_BEAM_TOKEN))

test('tinysd /q rejects the flux2 token', async () => {
  const response = await queueWithToken(routerUrl, env.GENERATED_ROUTER_FLUX2_AUTH_TOKEN)
  expect(response.status).toBe(401)
  expect(await response.json()).toEqual({ error: 'Unauthorized' })
})

test('tinysd /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('tinysd', routerUrl, env.GENERATED_ROUTER_TINYSD_AUTH_TOKEN)
  await expectImage(url)
})
