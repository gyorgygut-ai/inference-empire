import { expect, test } from 'vitest'
import { closeClients, connectClient, exchange, receiveMessage, withWorker } from './support.js'

test('interrupts an in-progress response and keeps the data channel usable', async () => {
  const result = await withWorker(async (url) => {
    const client = await connectClient(url)
    try {
      const firstChunk = receiveMessage(client.channel)
      client.channel.send(JSON.stringify({ type: 'stream', id: 'stream', values: ['one', 'two', 'three'] }))
      const first = await firstChunk
      const stoppedResponse = receiveMessage(client.channel)
      client.channel.send(JSON.stringify({ type: 'interrupt', id: 'stream' }))
      const stopped = await stoppedResponse
      const next = await exchange(client.channel, { type: 'input', id: 'after-interrupt', value: 'ready' })
      return [first, stopped, next]
    } finally {
      await closeClients(client.peer)
    }
  })

  expect(result).toEqual([
    { type: 'chunk', id: 'stream', index: 0, value: 'one' },
    { type: 'interrupted', id: 'stream' },
    { type: 'output', id: 'after-interrupt', value: 'ready' },
  ])
})
