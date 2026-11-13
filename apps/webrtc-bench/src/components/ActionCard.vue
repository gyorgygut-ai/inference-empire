<template>
  <section class="action-card">
    <header class="action-card__header">
      <h1>{{ title }}</h1>
    </header>
    <div class="action-card__content">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<style scoped>
.action-card {
  width: min(100%, 34rem);
  overflow: hidden;
  border: 1px solid #dce3ed;
  border-radius: 1rem;
  background: #fff;
  box-shadow: 0 1rem 2.5rem rgb(23 32 51 / 8%);
}

.action-card__header {
  padding: 1.25rem 1.5rem 0;
}

h1 {
  margin: 0;
  font-size: 1.25rem;
}

.action-card__content {
  display: grid;
  gap: 1rem;
  padding: 1.25rem 1.5rem 1.5rem;
}
</style>
