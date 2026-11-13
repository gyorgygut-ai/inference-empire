<template>
  <WorkerProbeCard title="Offer / answer" :worker-url="workerUrl" button-label="Negotiate" :loading="loading" :result="result" @run="run">
    <pre v-if="answer">{{ answer }}</pre>
  </WorkerProbeCard>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import WorkerProbeCard from './WorkerProbeCard.vue'
import { getClientSession } from './client-session'
import { useProbe } from './useProbe'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const answer = ref('')
const { loading, result, run } = useProbe(async () => {
  const session = await getClientSession()
  answer.value = session.sdp
  return 'WebRTC offer negotiated and data channel opened.'
})
</script>

<style scoped>
pre {
  max-height: 12rem;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
