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
  <section class="space-y-5">
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="text-2xl font-bold">Host dashboard</h2>
      <p class="badge badge-outline h-auto px-3 py-2">Game code: <strong class="ml-1">{{ code }}</strong></p>
    </div>
    <p v-if="store.error" class="alert alert-error" role="alert">{{ store.error }}</p>
    <template v-else>
      <p v-if="store.endReason" class="alert alert-info">
        {{ END_MESSAGES.host[store.endReason] }}
        <RouterLink class="link" :to="`/games/${code}/history`" data-test="history-link">View the game history</RouterLink>
      </p>
      <div v-else class="flex flex-wrap gap-3">
        <button
          v-if="!store.started"
          class="btn btn-primary dark:btn-neutral"
          type="button"
          data-test="start-game"
          @click="store.start(hostLink())"
        >
          Start game
        </button>
        <button
          v-else
          class="btn btn-primary dark:btn-neutral"
          type="button"
          data-test="draw-topic"
          @click="store.drawNext(hostLink())"
        >
          Draw topic
        </button>
        <button class="btn btn-outline" type="button" data-test="end-game" @click="store.end(hostLink())">
          End game
        </button>
      </div>
      <p v-if="store.windowOpen" class="alert alert-info" data-test="window-open">
        A claim is being settled. Draws resume in a moment.
      </p>
      <p v-if="store.actionError" class="alert alert-error" role="alert">{{ store.actionError }}</p>
      <DrawHistory :draws="store.draws" />
      <div class="grid gap-5 md:grid-cols-2">
        <PrizeBoard :prizes="store.prizes" />
        <ClaimLog :claims="store.claims" :message-for="store.messageFor" />
      </div>
      <LobbyList :players="store.players" />
    </template>
    <p v-if="store.poolName" class="text-base-content/70" data-test="pool-name">Pool: {{ store.poolName }}</p>
    <PoolColumns v-if="store.pool" :columns="store.pool" />
  </section>
</template>
