<template>
  <main>
    <WorkerServeProbe />
    <OfferAnswerProbe />
    <TurnConnectionProbe />
    <ArbitraryDataProbe />
    <ClientIsolationProbe />
    <InvalidInputProbe />
    <RealtimeInterruptProbe />
    <ConnectionFailureProbe />
  </main>
</template>

<script setup lang="ts">
import WorkerServeProbe from './worker/WorkerServeProbe.vue'
import OfferAnswerProbe from './worker/OfferAnswerProbe.vue'
import TurnConnectionProbe from './worker/TurnConnectionProbe.vue'
import ArbitraryDataProbe from './worker/ArbitraryDataProbe.vue'
import ClientIsolationProbe from './worker/ClientIsolationProbe.vue'
import InvalidInputProbe from './worker/InvalidInputProbe.vue'
import RealtimeInterruptProbe from './worker/RealtimeInterruptProbe.vue'
import ConnectionFailureProbe from './worker/ConnectionFailureProbe.vue'
</script>

<style>
:root {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #172033;
  background: #f2f5f9;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

body {
  margin: 0;
}

main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 25rem), 1fr));
  align-content: start;
  align-items: stretch;
  min-height: 100vh;
  padding: 2rem;
  gap: 1.5rem;
}
</style>
