<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchPools, type PoolSummary } from '../api/pools'
import { useLobbyStore } from '../stores/lobby'

const store = useLobbyStore()
const created = ref<{ code: string; hostLink: string } | null>(null)
const failed = ref(false)
const pools = ref<PoolSummary[]>([])
const poolId = ref<number | undefined>(undefined)

onMounted(async () => {
  try {
    pools.value = await fetchPools()
  } catch {
    // Without the list the host can still create a game on the default pool.
  }
})

async function createGame() {
  failed.value = false
  try {
    const game = await store.create(poolId.value)
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
    <label v-if="pools.length > 1">
      Pool
      <select v-model="poolId" data-test="pool-picker">
        <option v-for="pool in pools" :key="pool.id" :value="pool.is_default ? undefined : pool.id">
          {{ pool.name }}
        </option>
      </select>
    </label>
    <button type="button" data-test="create-game" @click="createGame">Create game</button>
    <p v-if="failed" role="alert">Could not create a game. Please try again.</p>
    <template v-if="created">
      <p>Game code: <strong>{{ created.code }}</strong></p>
      <p>
        Host link (keep it private, it controls the game):
        <code>{{ created.hostLink }}</code>
      </p>
    </template>
    <p><RouterLink to="/pools/new">Create a custom pool</RouterLink></p>
    <p><RouterLink to="/join">Join a game</RouterLink></p>
  </section>
</template>
