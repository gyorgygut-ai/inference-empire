import { expect, test } from 'vitest'
import { closeClients, connectClient, exchange, withWorker } from './support.js'

test('isolates concurrent browser clients', async () => {
  const result = await withWorker(async (url) => {
    const [first, second] = await Promise.all([connectClient(url), connectClient(url)])
    try {
      return await Promise.all([
        exchange(first.channel, { type: 'input', id: 'first', value: 'first-client' }),
        exchange(second.channel, { type: 'input', id: 'second', value: 'second-client' }),
      ])
    } finally {
      await closeClients(first.peer, second.peer)
    }
  })

  expect(result).toEqual([
    { type: 'output', id: 'first', value: 'first-client' },
    { type: 'output', id: 'second', value: 'second-client' },
  ])
})
