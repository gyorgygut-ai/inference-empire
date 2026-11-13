import { expect, test } from 'vitest'
import { closeClients, connectClient, exchange, receiveMessage, withWorker } from './support.js'

test('rejects invalid input and accepts a later valid message', async () => {
  const result = await withWorker(async (url) => {
    const client = await connectClient(url)
    try {
      const rejection = receiveMessage(client.channel)
      client.channel.send('{')
      const error = await rejection
      const output = await exchange(client.channel, { type: 'input', id: 'valid', value: 'still usable' })
      return [error, output]
    } finally {
      await closeClients(client.peer)
    }
  })

  expect(result).toEqual([
    { type: 'error', error: 'Invalid input' },
    { type: 'output', id: 'valid', value: 'still usable' },
  ])
})
