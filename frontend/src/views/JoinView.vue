<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'

const store = useSessionStore()
const router = useRouter()
const code = ref('')
const name = ref('')

async function submit() {
  const trimmedCode = code.value.trim().toUpperCase()
  const joined = await store.join(trimmedCode, name.value.trim())
  if (joined) {
    await router.push(`/games/${trimmedCode}`)
  }
}
</script>

<template>
  <section>
    <form @submit.prevent="submit">
      <label>
        Game code
        <input v-model="code" name="code" autocomplete="off" required />
      </label>
      <label>
        Your name
        <input v-model="name" name="name" autocomplete="off" required />
      </label>
      <button type="submit">Join</button>
    </form>
    <p v-if="store.error" role="alert">{{ store.error }}</p>
  </section>
</template>
