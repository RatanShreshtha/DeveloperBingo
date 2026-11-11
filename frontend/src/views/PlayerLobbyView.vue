<script setup lang="ts">
import { onMounted } from 'vue'
import { PRIZE_LABELS } from '../prizes'
import { useLobbyStore } from '../stores/lobby'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PrizeBoard from './PrizeBoard.vue'

const props = defineProps<{ code: string }>()
const store = useLobbyStore()

onMounted(() => {
  store.loadDrawHistory(props.code)
})
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.ended">
      {{ store.endReason === 'full_house' ? 'The game is over: the full house was claimed.' : 'The host ended the game.' }}
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
              :disabled="!store.drawnNames.includes(cell)"
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
        :disabled="store.isAwarded(entry.prize)"
        @click="store.claimPrize(entry.prize)"
      >Claim {{ PRIZE_LABELS[entry.prize] }}</button>
    </template>
    <PrizeBoard :prizes="store.prizes" />
    <DrawHistory :draws="store.draws" />
    <LobbyList :players="store.players" />
  </section>
</template>
