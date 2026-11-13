<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createGame as createRemoteGame } from '../api/games'
import { fetchPools, type PoolSummary } from '../api/pools'
import { useAsyncState } from '../composables/useAsyncState'
import { hostPath } from '../router'

const {
  data: created,
  error: createError,
  run: create,
} = useAsyncState<{ code: string; hostLink: string }>()
const {
  data: poolList,
  error: poolError,
  run: loadPools,
} = useAsyncState<PoolSummary[]>()
const pools = computed(() => poolList.value ?? [])
// The picked pool's id. The default pool has an id like any other, so every option has a value.
const pickedId = ref<number | undefined>(undefined)

onMounted(async () => {
  await loadPools(fetchPools)
  pickedId.value = pools.value.find((pool) => pool.is_default)?.id
})

async function createGame() {
  await create(async () => {
    const game = await createRemoteGame(
      pools.value.find((pool) => pool.id === pickedId.value),
    )
    return { code: game.code, hostLink: hostPath(game) }
  })
}
</script>

<template>
  <section class="mx-auto max-w-2xl space-y-6">
    <div class="space-y-2">
      <h2 class="text-3xl font-bold">Play DeveloperBingo</h2>
      <p class="text-base-content/70">
        Create a game to host, or join an existing game.
      </p>
    </div>
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body">
        <h3 class="card-title">Host a game</h3>
        <p v-if="poolError" class="alert alert-warning" role="alert">
          Could not load saved pools. You can still create a game with the
          default pool.
        </p>
        <label v-if="pools.length > 1" class="form-control block space-y-2">
          <span class="font-medium">Pool</span>
          <select
            v-model="pickedId"
            class="select select-bordered w-full"
            data-test="pool-picker"
          >
            <option v-for="pool in pools" :key="pool.id" :value="pool.id">
              {{ pool.name }}
            </option>
          </select>
        </label>
        <div class="card-actions">
          <button
            type="button"
            class="btn btn-primary dark:btn-neutral"
            data-test="create-game"
            @click="createGame"
          >
            Create game
          </button>
        </div>
        <p v-if="createError" class="alert alert-error" role="alert">
          Could not create a game. Please try again.
        </p>
        <div v-if="created" class="rounded-box bg-base-200 p-4">
          <p>
            Game code: <strong>{{ created.code }}</strong>
          </p>
          <p class="mt-2">
            Host link (keep it private, it controls the game):
            <code class="break-all">{{ created.hostLink }}</code>
          </p>
        </div>
        <p>
          <RouterLink class="link" to="/pools/new"
            >Create a custom pool</RouterLink
          >
        </p>
      </div>
    </div>
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body">
        <h3 class="card-title">Join a game</h3>
        <p>Have a game code? Join the lobby to get your ticket.</p>
        <div class="card-actions">
          <RouterLink class="btn btn-neutral" to="/join"
            >Join a game</RouterLink
          >
        </div>
      </div>
    </div>
  </section>
</template>
