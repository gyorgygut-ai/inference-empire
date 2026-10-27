import { test } from 'vitest'
import { envSchema } from '../../env.schema.dev'
import { expectImage, generateImage, inferenceTimeout, pingFrontend, pingRouter, pingWorker } from './acceptance-probes'

const env = envSchema.parse(process.env)
const routerUrl = `http://127.0.0.1:${env.ROUTER_FLUX2_PORT}`

test('workers-flux2 accepts an authenticated ping', () => pingWorker('workers-flux2', env.BEAM_TOKEN))

test('flux2 /q produces a downloadable image with its own token', { timeout: inferenceTimeout + 60000 }, async () => {
  const url = await generateImage('flux2', routerUrl, env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN)
  await expectImage(url)
})

test('face-value dev can reach its flux2 router', () => pingRouter(routerUrl, env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN))

test('face-value dev serves the app', () => pingFrontend(`http://127.0.0.1:${env.FACE_VALUE_PORT}`))
