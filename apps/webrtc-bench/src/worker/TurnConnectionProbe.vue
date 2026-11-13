<template>
  <WorkerProbeCard title="TURN connection" :worker-url="workerUrl" button-label="Verify relay" :loading="loading" :result="result" @run="run" />
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { getClientSession } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const { loading, result, run } = useProbe(async () => {
  const { peer } = await getClientSession()
  const stats = await peer.getStats()
  const pair = [...stats.values()].find((stat) => stat.type === 'candidate-pair' && stat.state === 'succeeded' && stat.nominated)
  if (!pair) {
    throw new Error('No selected candidate pair')
  }
  const candidate = stats.get(pair.localCandidateId)
  if (!candidate || candidate.type !== 'local-candidate' || candidate.candidateType !== 'relay') {
    throw new Error('Selected candidate pair is not relayed')
  }
  return `Selected local candidate: ${candidate.candidateType}`
})
</script>
