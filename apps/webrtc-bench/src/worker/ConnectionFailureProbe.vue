<template>
  <WorkerProbeCard title="Connection failure recovery" :worker-url="workerUrl" button-label="Reconnect" :loading="loading" :result="result" @run="run" />
</template>

<script setup lang="ts">
import WorkerProbeCard from './WorkerProbeCard.vue'
import { createIndependentClientSession, getClientSession, resetClientSession, sendAndReceive } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const { loading, result, run } = useProbe(async () => {
  const active = await getClientSession()
  const failed = await createIndependentClientSession()
  failed.peer.close()
  const activeOutput = await sendAndReceive(active, { type: 'input', id: 'active-client', value: 'unaffected' }, (value) => value.id === 'active-client')
  await resetClientSession()
  const recovered = await getClientSession()
  const recoveredOutput = await sendAndReceive(recovered, { type: 'input', id: 'recovered', value: 'connected' }, (value) => value.id === 'recovered')
  if (activeOutput.type !== 'output' || recoveredOutput.type !== 'output') {
    throw new Error(JSON.stringify([activeOutput, recoveredOutput]))
  }
  return JSON.stringify([activeOutput, recoveredOutput])
})
</script>
