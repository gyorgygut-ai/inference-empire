import { expect, test } from 'vitest'
import { closeClients, connectClient, exchange, withWorker } from './support.js'

test('echoes arbitrary JSON data', async () => {
  const result = await withWorker(async (url) => {
    const client = await connectClient(url)
    try {
      return await exchange(client.channel, { type: 'input', id: 'arbitrary', value: { nested: [1, true, null] } })
    } finally {
      await closeClients(client.peer)
    }
  })

  expect(result).toEqual({ type: 'output', id: 'arbitrary', value: { nested: [1, true, null] } })
})
