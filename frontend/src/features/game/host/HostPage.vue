<script setup lang="ts">
import { onMounted } from 'vue'
import type { HostLink } from '../../../api/games'
import { useHostSession } from '../../../stores/session'
import { messageFor } from '../shared/errors'
import DrawHistory from '../shared/DrawHistory.vue'
import EndBanner from '../shared/EndBanner.vue'
import GameHeader from '../shared/GameHeader.vue'
import LobbyList from '../shared/LobbyList.vue'
import PrizeBoard from '../shared/PrizeBoard.vue'
import ClaimLog from './ClaimLog.vue'
import PoolColumns from './PoolColumns.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useHostSession()

function hostLink(): HostLink {
  return { code: props.code, host_token: props.token ?? '' }
}

onMounted(() => {
  store.watchAsHost(hostLink())
})
</script>

<template>
  <section class="space-y-5">
    <GameHeader title="Host dashboard" :code="code" />
    <p v-if="store.error" class="alert alert-error" role="alert">{{ store.error }}</p>
    <template v-else>
      <EndBanner v-if="store.endReason" role="host" :reason="store.endReason" :code="code" />
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
        <ClaimLog :claims="store.claims" :message-for="messageFor" />
      </div>
      <LobbyList :players="store.players" />
    </template>
    <p v-if="store.poolName" class="text-base-content/70" data-test="pool-name">Pool: {{ store.poolName }}</p>
    <PoolColumns v-if="store.pool" :columns="store.pool" />
  </section>
</template>
