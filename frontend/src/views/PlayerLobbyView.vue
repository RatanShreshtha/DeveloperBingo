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
  <section class="space-y-5">
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="text-2xl font-bold">Your game</h2>
      <p class="badge badge-outline h-auto px-3 py-2">Game code: <strong class="ml-1">{{ code }}</strong></p>
    </div>
    <p v-if="store.replaced" class="alert alert-warning" role="alert" data-test="replaced">
      This game was opened in another window, so this one has left it.
    </p>
    <p v-else-if="resuming && !inGame">Rejoining the game…</p>
    <template v-else-if="!inGame">
      <p v-if="store.error" class="alert alert-error" role="alert">{{ store.error }}</p>
      <RouterLink class="btn btn-primary dark:btn-neutral" to="/join" data-test="join-link">Join this game</RouterLink>
    </template>
    <template v-else>
      <p v-if="store.endReason" class="alert alert-info">
        {{ END_MESSAGES.player[store.endReason] }}
        <RouterLink class="link" :to="`/games/${code}/history`" data-test="history-link">View the game history</RouterLink>
      </p>
      <p v-else-if="store.started" class="alert">The game has started.</p>
      <p v-else class="alert">Waiting for the host to start the game.</p>
      <div v-if="store.ticket" class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Your ticket</h3>
          <p class="text-sm text-base-content/70 lg:hidden">Scroll sideways to see the full ticket.</p>
          <div class="overflow-x-auto" role="region" aria-label="Your ticket, scroll horizontally" tabindex="0">
            <table class="ticket w-full min-w-[48rem] table-fixed border-separate border-spacing-1" aria-label="Your ticket">
              <tbody>
                <tr v-for="(line, lineIndex) in store.ticket" :key="lineIndex">
                  <td
                    v-for="(cell, columnIndex) in line"
                    :key="columnIndex"
                    class="h-16 rounded-lg bg-base-200"
                    data-test="ticket-cell"
                  >
                    <button
                      v-if="cell"
                      type="button"
                      class="btn btn-sm h-full min-h-16 w-full text-[0.6875rem] whitespace-normal break-words leading-tight disabled:!border-base-300 disabled:!bg-base-200 disabled:!text-base-content disabled:!opacity-100"
                      :class="store.ticks.includes(cell) ? 'btn-success text-black' : 'btn-outline'"
                      data-test="tick-cell"
                      :aria-pressed="store.ticks.includes(cell)"
                      :disabled="store.ended || !store.drawnNames.includes(cell)"
                      @click="store.toggleTick(cell)"
                    >{{ cell }}<span v-if="store.ticks.includes(cell)" aria-hidden="true"> ✓</span></button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <p v-if="store.actionError" class="alert alert-error" role="alert">{{ store.actionError }}</p>
      <DrawHistory :draws="store.draws" />
      <div class="grid gap-5 md:grid-cols-2">
        <PrizeBoard :prizes="store.prizes" />
        <section v-if="store.started && !store.ended" class="card bg-base-100 shadow-sm">
          <div class="card-body">
            <h2 class="card-title">Claim</h2>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="entry in store.prizes"
                :key="entry.prize"
                type="button"
                class="btn btn-outline"
                :data-test="`claim-${entry.prize}`"
                :disabled="store.isAwarded(entry.prize) || store.isPending(entry.prize)"
                @click="store.claimPrize(entry.prize)"
              >{{ store.isPending(entry.prize) ? 'Claiming' : 'Claim' }} {{ PRIZE_LABELS[entry.prize] }}{{ store.isPending(entry.prize) ? '…' : '' }}</button>
            </div>
          </div>
        </section>
      </div>
      <LobbyList :players="store.players" />
    </template>
  </section>
</template>
