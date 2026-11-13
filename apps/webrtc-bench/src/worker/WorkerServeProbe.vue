<template>
  <ActionCard title="Worker serve probe">
    <p class="worker-url"><strong>Worker URL:</strong> {{ workerUrl }}</p>
    <PrimaryButton :disabled="isLoading" @click="probeWorker">
      {{ isLoading ? 'Testing…' : 'Test' }}
    </PrimaryButton>
    <ActionResult v-if="result" :status="result.status" :message="result.message" />
  </ActionCard>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ActionCard from '../components/ActionCard.vue'
import ActionResult from '../components/ActionResult.vue'
import PrimaryButton from '../components/PrimaryButton.vue'

const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL
const isLoading = ref(false)
const result = ref<{ status: 'success' | 'failure'; message: string } | null>(null)

async function probeWorker() {
  isLoading.value = true
  result.value = null

  try {
    const response = await fetch(workerUrl)
    const body = await response.text()

    if (!response.ok || body !== 'ok') {
      result.value = {
        status: 'failure',
        message: `HTTP ${response.status}: ${body || response.statusText}`,
      }
      return
    }

    result.value = { status: 'success', message: `HTTP ${response.status}: ${body}` }
  } catch (error) {
    result.value = {
      status: 'failure',
      message: error instanceof Error ? error.message : 'Worker request failed',
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.worker-url {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>
