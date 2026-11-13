<template>
  <WorkerProbeCard title="Invalid input" :worker-url="workerUrl" button-label="Test rejection" :loading="loading" :result="result" @run="run" />
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { getClientSession, sendAndReceive } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const { loading, result, run } = useProbe(async () => {
  const session = await getClientSession()
  const rejection = await sendAndReceive(session, '{', (value) => value.type === 'error')
  const output = await sendAndReceive(session, { type: 'input', id: 'after-invalid', value: 'usable' }, (value) => value.id === 'after-invalid')
  if (rejection.error !== 'Invalid input' || output.type !== 'output') {
    throw new Error(JSON.stringify([rejection, output]))
  }
  return JSON.stringify([rejection, output])
})
</script>
