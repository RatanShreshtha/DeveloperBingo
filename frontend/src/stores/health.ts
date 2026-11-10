import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchHealth, type HealthResponse } from '../api/health'

export const useHealthStore = defineStore('health', () => {
  const health = ref<HealthResponse | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  async function load() {
    loading.value = true
    error.value = null
    try {
      health.value = await fetchHealth()
    } catch {
      health.value = null
      error.value = 'Could not reach the backend'
    } finally {
      loading.value = false
    }
  }

  return { health, error, loading, load }
})
