<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDefaultPool, type TopicResponse } from '../api/pools'
import type { HostLink } from '../api/games'
import { useLobbyStore } from '../stores/lobby'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PrizeBoard from './PrizeBoard.vue'
import PoolColumns from './PoolColumns.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useLobbyStore()
const pool = ref<TopicResponse[][] | null>(null)
const poolError = ref(false)

function hostLink(): HostLink {
  return { code: props.code, host_token: props.token ?? '' }
}

onMounted(async () => {
  store.watchAsHost(hostLink())
  store.loadDrawHistory(props.code)
  try {
    pool.value = (await fetchDefaultPool()).columns
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
      <p v-if="store.ended">
        {{ store.endReason === 'full_house' ? 'The game is over: the full house was claimed.' : 'You ended the game.' }}
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
      <DrawHistory :draws="store.draws" />
      <LobbyList :players="store.players" />
    </template>
    <PoolColumns v-if="pool" :columns="pool" />
    <p v-else-if="poolError" role="alert">Could not load the default pool.</p>
  </section>
</template>
