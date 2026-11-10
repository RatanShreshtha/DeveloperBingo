<script setup lang="ts">
import { ref } from 'vue'
import { useLobbyStore } from '../stores/lobby'

const store = useLobbyStore()
const created = ref<{ code: string; hostLink: string } | null>(null)
const failed = ref(false)

async function createGame() {
  failed.value = false
  try {
    const game = await store.create()
    created.value = {
      code: game.code,
      hostLink: `/host/${game.code}?token=${game.host_token}`,
    }
  } catch {
    failed.value = true
  }
}
</script>

<template>
  <section>
    <button type="button" data-test="create-game" @click="createGame">Create game</button>
    <p v-if="failed" role="alert">Could not create a game. Please try again.</p>
    <template v-if="created">
      <p>Game code: <strong>{{ created.code }}</strong></p>
      <p>
        Host link (keep it private, it controls the game):
        <code>{{ created.hostLink }}</code>
      </p>
    </template>
    <p><RouterLink to="/join">Join a game</RouterLink></p>
  </section>
</template>
