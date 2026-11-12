<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePlayerSession } from '../../../stores/session'
import DrawHistory from '../shared/DrawHistory.vue'
import EndBanner from '../shared/EndBanner.vue'
import GameHeader from '../shared/GameHeader.vue'
import LobbyList from '../shared/LobbyList.vue'
import PrizeBoard from '../shared/PrizeBoard.vue'
import ClaimPanel from './ClaimPanel.vue'
import TicketGrid from './TicketGrid.vue'

const props = defineProps<{ code: string }>()
const store = usePlayerSession()
// The game shows only while the store holds this player in it: a reload with nothing to rejoin
// with, a refused rejoin and being replaced all leave the player asking to join again.
const inGame = computed(() => store.player?.code === props.code)
// True until the first rejoin on opening the page has answered, so the join link doesn't flash.
const resuming = ref(true)

onMounted(async () => {
  await store.resume(props.code)
  resuming.value = false
})
</script>

<template>
  <section class="space-y-5">
    <GameHeader title="Your game" :code="code" />
    <p v-if="store.replaced" class="alert alert-warning" role="alert" data-test="replaced">
      This game was opened in another window, so this one has left it.
    </p>
    <p v-else-if="resuming && !inGame">Rejoining the game…</p>
    <template v-else-if="!inGame">
      <p v-if="store.error" class="alert alert-error" role="alert">{{ store.error }}</p>
      <RouterLink class="btn btn-primary dark:btn-neutral" to="/join" data-test="join-link">Join this game</RouterLink>
    </template>
    <template v-else>
      <EndBanner v-if="store.endReason" role="player" :reason="store.endReason" :code="code" />
      <p v-else-if="store.started" class="alert">The game has started.</p>
      <p v-else class="alert">Waiting for the host to start the game.</p>
      <TicketGrid
        v-if="store.ticket"
        :ticket="store.ticket"
        :ticks="store.ticks"
        :drawn="store.drawnNames"
        :ended="store.ended"
        @toggle="store.toggleTick"
      />
      <p v-if="store.actionError" class="alert alert-error" role="alert">{{ store.actionError }}</p>
      <DrawHistory :draws="store.draws" />
      <div class="grid gap-5 md:grid-cols-2">
        <PrizeBoard :prizes="store.prizes" />
        <ClaimPanel
          v-if="store.started && !store.ended"
          :prizes="store.prizes"
          :pending="store.pendingClaims"
          @claim="store.claimPrize"
        />
      </div>
      <LobbyList :players="store.players" />
    </template>
  </section>
</template>
