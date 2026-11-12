<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchGamePool, type TopicResponse } from '../api/pools'
import type { HostLink } from '../api/games'
import { END_MESSAGES } from '../endMessages'
import { useLobbyStore } from '../stores/lobby'
import ClaimLog from './ClaimLog.vue'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PrizeBoard from './PrizeBoard.vue'
import PoolColumns from './PoolColumns.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useLobbyStore()
const pool = ref<TopicResponse[][] | null>(null)
const poolName = ref<string | null>(null)
const poolError = ref(false)

function hostLink(): HostLink {
  return { code: props.code, host_token: props.token ?? '' }
}

onMounted(async () => {
  store.watchAsHost(hostLink())
  store.loadDrawHistory(props.code)
  try {
    const gamePool = await fetchGamePool(props.code)
    pool.value = gamePool.columns
    poolName.value = gamePool.name ?? null
  } catch {
    poolError.value = true
  }
})
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.error" role="alert">{{ store.error }}</p>
    <template v-else>
      <p v-if="store.endReason">
        {{ END_MESSAGES.host[store.endReason] }}
        <RouterLink :to="`/games/${code}/history`" data-test="history-link">View the game history</RouterLink>
      </p>
      <div v-else>
        <button
          v-if="!store.started"
          type="button"
          data-test="start-game"
          @click="store.start(hostLink())"
        >
          Start game
        </button>
        <button
          v-else
          type="button"
          data-test="draw-topic"
          @click="store.drawNext(hostLink())"
        >
          Draw topic
        </button>
        <button type="button" data-test="end-game" @click="store.end(hostLink())">
          End game
        </button>
      </div>
      <p v-if="store.actionError" role="alert">{{ store.actionError }}</p>
      <PrizeBoard :prizes="store.prizes" />
      <ClaimLog :claims="store.claims" :message-for="store.messageFor" />
      <DrawHistory :draws="store.draws" />
      <LobbyList :players="store.players" />
    </template>
    <p v-if="poolName" data-test="pool-name">Pool: {{ poolName }}</p>
    <PoolColumns v-if="pool" :columns="pool" />
    <p v-else-if="poolError" role="alert">Could not load this game's pool.</p>
  </section>
</template>
