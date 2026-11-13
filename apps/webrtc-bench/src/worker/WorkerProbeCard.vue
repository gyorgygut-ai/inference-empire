<template>
  <ActionCard :title="title">
    <p><strong>Worker URL:</strong> {{ workerUrl }}</p>
    <slot />
    <PrimaryButton :disabled="loading" @click="$emit('run')">
      {{ loading ? 'Working…' : buttonLabel }}
    </PrimaryButton>
    <ActionResult v-if="result" :status="result.status" :message="result.message" />
  </ActionCard>
</template>

<script setup lang="ts">
import ActionCard from '../components/ActionCard.vue'
import ActionResult from '../components/ActionResult.vue'
import PrimaryButton from '../components/PrimaryButton.vue'

defineProps<{
  title: string
  workerUrl: string
  buttonLabel: string
  loading: boolean
  result: { status: 'success' | 'failure'; message: string } | null
}>()

defineEmits<{ run: [] }>()
</script>

<style scoped>
p {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>
