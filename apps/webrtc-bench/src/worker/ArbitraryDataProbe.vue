<template>
  <WorkerProbeCard title="Arbitrary JSON data" :worker-url="workerUrl" button-label="Send JSON" :loading="loading" :result="result" @run="run">
    <pre>{{ input }}</pre>
  </WorkerProbeCard>
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { getClientSession, sendAndReceive } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const input = { type: 'input', id: 'bench-arbitrary', value: { message: 'hello', values: [1, true, null] } }
const { loading, result, run } = useProbe(async () => {
  const response = await sendAndReceive(await getClientSession(), input, (value) => value.id === input.id)
  if (response.type !== 'output') {
    throw new Error(JSON.stringify(response))
  }
  return JSON.stringify(response)
})
</script>

<style scoped>
pre {
  margin: 0;
  white-space: pre-wrap;
}
</style>
