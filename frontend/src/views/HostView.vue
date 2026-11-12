<script setup lang="ts">
import { onMounted } from 'vue'
import type { HostLink } from '../api/games'
import { END_MESSAGES } from '../endMessages'
import { useSessionStore } from '../stores/session'
import ClaimLog from './ClaimLog.vue'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PrizeBoard from './PrizeBoard.vue'
import PoolColumns from './PoolColumns.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useSessionStore()

function hostLink(): HostLink {
  return { code: props.code, host_token: props.token ?? '' }
}

onMounted(() => {
  store.watchAsHost(hostLink())
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
      <p v-if="store.windowOpen" data-test="window-open">
        A claim is being settled. Draws resume in a moment.
      </p>
      <p v-if="store.actionError" role="alert">{{ store.actionError }}</p>
      <PrizeBoard :prizes="store.prizes" />
      <ClaimLog :claims="store.claims" :message-for="store.messageFor" />
      <DrawHistory :draws="store.draws" />
      <LobbyList :players="store.players" />
    </template>
    <p v-if="store.poolName" data-test="pool-name">Pool: {{ store.poolName }}</p>
    <PoolColumns v-if="store.pool" :columns="store.pool" />
  </section>
</template>
