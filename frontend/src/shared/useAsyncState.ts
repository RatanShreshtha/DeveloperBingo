import { ref, shallowRef } from 'vue'

export function useAsyncState<T>() {
  const data = shallowRef<T | null>(null)
  const error = shallowRef<Error | null>(null)
  const pending = ref(false)
  let latest = 0

  async function run(operation: () => Promise<T>): Promise<void> {
    const request = ++latest
    pending.value = true
    error.value = null
    try {
      const result = await operation()
      if (request === latest) {
        data.value = result
      }
    } catch (cause) {
      if (request === latest) {
        error.value = cause instanceof Error ? cause : new Error('Request failed', { cause })
      }
    } finally {
      if (request === latest) {
        pending.value = false
      }
    }
  }

  return { data, error, pending, run }
}
