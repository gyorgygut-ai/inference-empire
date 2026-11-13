<template>
  <button class="primary-button" :disabled="disabled" type="button" @click="$emit('click')">
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ disabled?: boolean }>()
defineEmits<{ click: [] }>()
</script>

<style scoped>
.primary-button {
  justify-self: start;
  border: 0;
  border-radius: 0.5rem;
  padding: 0.7rem 1rem;
  color: white;
  background: #2459d3;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}

.primary-button:hover:not(:disabled) {
  background: #1948b6;
}

.primary-button:disabled {
  cursor: wait;
  opacity: 0.65;
}
</style>
