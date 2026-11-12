<script setup lang="ts">
import { onMounted } from 'vue'
import { useHealthStore } from '../stores/health'

const store = useHealthStore()

onMounted(() => {
  store.load()
})
</script>

<template>
  <section class="health border-t border-base-300 pt-4 text-sm text-base-content/70">
    <p v-if="store.loading">Checking backend…</p>
    <p v-else-if="store.error" class="text-error" role="alert">{{ store.error }}</p>
    <div v-else-if="store.health" class="flex flex-wrap gap-x-4 gap-y-1">
      <p>Status: {{ store.health.status }}</p>
      <p>Database: {{ store.health.database }}</p>
    </div>
  </section>
</template>
