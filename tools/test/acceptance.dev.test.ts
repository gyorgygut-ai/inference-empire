import { test } from 'vitest'
import { configSchema } from '../../packages/schemas/config.schema'
import { devSecretsSchema } from '../../packages/schemas/secrets.schema'
import { expectImage, generateImage, inferenceTimeout, pingFrontend, pingRouter, pingWorker } from './acceptance-probes'

const env = { ...configSchema.parse(process.env), ...devSecretsSchema.parse(process.env) }
const routerUrl = `http://127.0.0.1:${env.DEV_ROUTER_FLUX2_PORT}`

test('worker-flux2 accepts an authenticated ping', () => pingWorker('worker-flux2', env.SECRET_BEAM_TOKEN))

test('flux2 /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('flux2', routerUrl, env.ROUTER_FLUX2_AUTH_TOKEN)
  await expectImage(url)
})

test('face-value dev can reach its flux2 router', () => pingRouter(routerUrl, env.ROUTER_FLUX2_AUTH_TOKEN))

test('face-value dev serves the app', () => pingFrontend(`http://127.0.0.1:${env.DEV_FACE_VALUE_PORT}`))
