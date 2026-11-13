import { expect, test } from 'vitest'
import { closeClients, connectClient, withWorker } from './support.js'
import type { RTCIceCandidatePairStats, RTCIceCandidateStats, RTCIceServer } from 'werift'

test('establishes a relayed data-channel connection', async () => {
  const result = await withWorker(async (url) => {
    const response = await fetch(`${url}/ice-configuration`)
    const { iceServers } = await response.json() as { iceServers: RTCIceServer[] }
    const client = await connectClient(url, iceServers, true)
    try {
      const stats = [...(await client.peer.getStats()).values()]
      const pairs = stats.filter((stat): stat is RTCIceCandidatePairStats => {
        const pair = stat as RTCIceCandidatePairStats
        return pair.type === 'candidate-pair' && pair.state === 'succeeded' && pair.nominated === true
      })
      return pairs.some((pair) => stats.some((stat) => {
        const candidate = stat as RTCIceCandidateStats
        return candidate.type === 'local-candidate' && candidate.id === pair.localCandidateId && candidate.candidateType === 'relay'
      }))
    } finally {
      await closeClients(client.peer)
    }
  })

  expect(result).toBe(true)
})
