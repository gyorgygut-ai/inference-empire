import { expect, test } from 'vitest'
import { closeClients, connectClient, withWorker } from './support.js'

test('returns an SDP answer and rejects an invalid offer', async () => {
  const result = await withWorker(async (url) => {
    const client = await connectClient(url)
    try {
      const invalidOffer = await fetch(`${url}/offer`, { method: 'POST', body: 'not an SDP offer' })
      return { channel: client.channel.readyState, signaling: client.peer.signalingState, invalidStatus: invalidOffer.status }
    } finally {
      await closeClients(client.peer)
    }
  })

  expect(result).toEqual({ channel: 'open', signaling: 'stable', invalidStatus: 400 })
})
