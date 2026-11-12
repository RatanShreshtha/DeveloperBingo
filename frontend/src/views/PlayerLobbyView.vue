<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { PRIZE_LABELS } from '../prizes'
import { END_MESSAGES } from '../endMessages'
import { useSessionStore } from '../stores/session'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PrizeBoard from './PrizeBoard.vue'

const props = defineProps<{ code: string }>()
const store = useSessionStore()
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
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.replaced" role="alert" data-test="replaced">
      This game was opened in another window, so this one has left it.
    </p>
    <p v-else-if="resuming && !inGame">Rejoining the game…</p>
    <template v-else-if="!inGame">
      <p v-if="store.error" role="alert">{{ store.error }}</p>
      <RouterLink to="/join" data-test="join-link">Join this game</RouterLink>
    </template>
    <template v-else>
    <p v-if="store.endReason">
      {{ END_MESSAGES.player[store.endReason] }}
      <RouterLink :to="`/games/${code}/history`" data-test="history-link">View the game history</RouterLink>
    </p>
    <p v-else-if="store.started">The game has started.</p>
    <p v-else>Waiting for the host to start the game.</p>
    <table v-if="store.ticket" class="ticket" aria-label="Your ticket">
      <tbody>
        <tr v-for="(line, lineIndex) in store.ticket" :key="lineIndex">
          <td
            v-for="(cell, columnIndex) in line"
            :key="columnIndex"
            data-test="ticket-cell"
          >
            <button
              v-if="cell"
              type="button"
              data-test="tick-cell"
              :aria-pressed="store.ticks.includes(cell)"
              :disabled="store.ended || !store.drawnNames.includes(cell)"
              @click="store.toggleTick(cell)"
            >{{ cell }}<span v-if="store.ticks.includes(cell)" aria-hidden="true"> ✓</span></button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="store.actionError" role="alert">{{ store.actionError }}</p>
    <template v-if="store.started && !store.ended">
      <button
        v-for="entry in store.prizes"
        :key="entry.prize"
        type="button"
        :data-test="`claim-${entry.prize}`"
        :disabled="store.isAwarded(entry.prize) || store.isPending(entry.prize)"
        @click="store.claimPrize(entry.prize)"
      >{{ store.isPending(entry.prize) ? 'Claiming' : 'Claim' }} {{ PRIZE_LABELS[entry.prize] }}{{ store.isPending(entry.prize) ? '…' : '' }}</button>
    </template>
    <PrizeBoard :prizes="store.prizes" />
    <DrawHistory :draws="store.draws" />
    <LobbyList :players="store.players" />
    </template>
  </section>
</template>
