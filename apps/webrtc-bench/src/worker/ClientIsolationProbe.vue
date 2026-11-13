<template>
  <WorkerProbeCard title="Concurrent client isolation" :worker-url="workerUrl" button-label="Test clients" :loading="loading" :result="result" @run="run" />
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { createIndependentClientSession, sendAndReceive } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const { loading, result, run } = useProbe(async () => {
  const [first, second] = await Promise.all([createIndependentClientSession(), createIndependentClientSession()])
  try {
    const [firstOutput, secondOutput] = await Promise.all([
      sendAndReceive(first, { type: 'input', id: 'client-a', value: 'client A' }, (value) => value.id === 'client-a'),
      sendAndReceive(second, { type: 'input', id: 'client-b', value: 'client B' }, (value) => value.id === 'client-b'),
    ])
    if (firstOutput.value !== 'client A' || secondOutput.value !== 'client B') {
      throw new Error('Client responses were not isolated')
    }
    return JSON.stringify([firstOutput, secondOutput])
  } finally {
    first.peer.close()
    second.peer.close()
  }
})
</script>
