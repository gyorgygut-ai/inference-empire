import { getRequestListener } from '@hono/node-server'
import { handle } from '../src/handler.js'
import { envSchema } from '../env.schema.js'

export default getRequestListener((request) => handle(request, envSchema.parse(process.env)))
