import { afterAll, expect, test } from 'vitest'
import { server } from '../src/server.js'

afterAll(() => {
  server.close()
})

test('serves a health response on WORKER_WEBRTC_PORT', async () => {
  const response = await fetch(`http://127.0.0.1:${process.env.WORKER_WEBRTC_PORT}`)

  expect(response.status).toBe(200)
  expect(await response.text()).toBe('ok')
})
