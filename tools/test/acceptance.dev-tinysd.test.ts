import { expect, test } from 'vitest'
import { envSchema } from '../../env.schema.dev'
import { expectImage, generateImage, inferenceTimeout, pingWorker, queueWithToken } from './acceptance-probes'

const env = envSchema.parse(process.env)
const routerUrl = `http://127.0.0.1:${env.ROUTER_TINYSD_PORT}`

test('workers-tiny_sd accepts an authenticated ping', () => pingWorker('workers-tiny_sd', env.BEAM_TOKEN))

test('tinysd /q rejects the flux2 token', async () => {
  const response = await queueWithToken(routerUrl, env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN)
  expect(response.status).toBe(401)
  expect(await response.json()).toEqual({ error: 'Unauthorized' })
})

test('tinysd /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('tinysd', routerUrl, env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN)
  await expectImage(url)
})
