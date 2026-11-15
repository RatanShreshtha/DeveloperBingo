<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { usePlayerSession } from '../stores/session'

const store = usePlayerSession()
const router = useRouter()
const code = ref('')
const name = ref('')

// The store's error may still hold a refusal from another page, such as the game page.
onMounted(() => {
  store.error = null
})

async function submit() {
  const trimmedCode = code.value.trim().toUpperCase()
  const joined = await store.join(trimmedCode, name.value.trim())
  if (joined) {
    await router.push(`/games/${trimmedCode}`)
  }
}
</script>

<template>
  <section class="mx-auto max-w-xl">
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body">
        <h1 class="card-title">Join a game</h1>
        <form class="space-y-4" @submit.prevent="submit">
          <label class="block space-y-2">
            <span class="font-medium">Game code</span>
            <input
              v-model="code"
              class="input input-bordered w-full"
              name="code"
              autocomplete="off"
              required
            />
          </label>
          <label class="block space-y-2">
            <span class="font-medium">Your name</span>
            <input
              v-model="name"
              class="input input-bordered w-full"
              name="name"
              autocomplete="off"
              required
            />
          </label>
          <button class="btn btn-soft btn-primary gap-2" type="submit">
            <AppIcon name="join" />
            Join
          </button>
        </form>
        <p v-if="store.error" class="alert alert-error" role="alert">
          {{ store.error }}
        </p>
      </div>
    </div>
  </section>
</template>
