<template>
  <p class="action-result" :class="`action-result--${status}`" role="status" aria-live="polite">
    <span aria-hidden="true">{{ status === 'success' ? '✅' : '❌' }}</span>
    <span>{{ message }}</span>
  </p>
</template>

<script setup lang="ts">
defineProps<{
  status: 'success' | 'failure'
  message: string
}>()
</script>

<style scoped>
.action-result {
  display: flex;
  gap: 0.55rem;
  margin: 0;
  overflow-wrap: anywhere;
}

.action-result--success {
  color: #17643c;
}

.action-result--failure {
  color: #a12b35;
}
</style>
