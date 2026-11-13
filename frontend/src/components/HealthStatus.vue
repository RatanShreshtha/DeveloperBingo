<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { fetchHealth, type HealthResponse } from '../api/health'
import { HttpError } from '../api/request'
import { useAsyncState } from '../composables/useAsyncState'

const {
  data: health,
  error,
  pending: loading,
  run,
} = useAsyncState<HealthResponse>()
const errorMessage = computed(() => {
  if (!error.value) return null
  return error.value instanceof HttpError
    ? `Backend health check failed with status ${error.value.status}`
    : 'Could not reach the backend'
})

onMounted(() => {
  void run(fetchHealth)
})
</script>

<template>
  <section
    class="health border-t border-base-300 pt-4 text-sm text-base-content/70"
  >
    <p v-if="loading">Checking backend…</p>
    <p v-else-if="errorMessage" class="text-error" role="alert">
      {{ errorMessage }}
    </p>
    <div v-else-if="health" class="flex flex-wrap gap-x-4 gap-y-1">
      <p>Status: {{ health.status }}</p>
      <p>Database: {{ health.database }}</p>
    </div>
  </section>
</template>
