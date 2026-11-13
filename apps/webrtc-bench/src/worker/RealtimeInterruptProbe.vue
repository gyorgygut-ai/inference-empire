<template>
  <WorkerProbeCard title="Realtime interrupt" :worker-url="workerUrl" button-label="Interrupt stream" :loading="loading" :result="result" @run="run" />
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { getClientSession, sendAndReceive } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const { loading, result, run } = useProbe(async () => {
  const session = await getClientSession()
  const firstChunk = await sendAndReceive(session, { type: 'stream', id: 'bench-stream', values: ['first', 'second', 'third'] }, (value) => value.id === 'bench-stream' && value.type === 'chunk')
  const interrupted = await sendAndReceive(session, { type: 'interrupt', id: 'bench-stream' }, (value) => value.id === 'bench-stream' && value.type === 'interrupted')
  const output = await sendAndReceive(session, { type: 'input', id: 'after-interrupt', value: 'ready' }, (value) => value.id === 'after-interrupt')
  if (output.type !== 'output') {
    throw new Error(JSON.stringify([firstChunk, interrupted, output]))
  }
  return JSON.stringify([firstChunk, interrupted, output])
})
</script>
