import { expect, test } from 'vitest'
import { withWorker } from './support.js'

test('serves health with open CORS', async () => {
  const result = await withWorker(async (url) => {
    const response = await fetch(url, { headers: { origin: 'https://bench.example' } })
    return { status: response.status, body: await response.text(), cors: response.headers.get('access-control-allow-origin') }
  })

  expect(result).toEqual({ status: 200, body: 'ok', cors: '*' })
})
