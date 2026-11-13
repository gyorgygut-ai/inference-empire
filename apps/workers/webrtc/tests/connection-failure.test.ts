import { expect, test } from 'vitest'
import { closeClients, connectClient, exchange, withWorker } from './support.js'

test('contains a failed client connection and accepts new clients', async () => {
  const result = await withWorker(async (url) => {
    const [failed, active] = await Promise.all([connectClient(url), connectClient(url)])
    try {
      await closeClients(failed.peer)
      const activeOutput = await exchange(active.channel, { type: 'input', id: 'active', value: 'unaffected' })
      const recovered = await connectClient(url)
      try {
        const recoveredOutput = await exchange(recovered.channel, { type: 'input', id: 'recovered', value: 'new client' })
        return [activeOutput, recoveredOutput]
      } finally {
        await closeClients(recovered.peer)
      }
    } finally {
      await closeClients(active.peer)
    }
  })

  expect(result).toEqual([
    { type: 'output', id: 'active', value: 'unaffected' },
    { type: 'output', id: 'recovered', value: 'new client' },
  ])
})
