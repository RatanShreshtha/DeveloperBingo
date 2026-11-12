<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { fetchGameHistory, type GameHistoryResponse } from '../../api/games'
import { HttpError } from '../../api/request'
import { useAsyncState } from '../../shared/useAsyncState'
import { newestDrawsFirst } from '../game/shared/draws'
import { PRIZE_LABELS } from '../game/shared/prizes'
import { messageFor } from '../game/shared/errors'

const props = defineProps<{ code: string }>()
const { data: history, error, run } = useAsyncState<GameHistoryResponse>()
const latestDraws = computed(() => newestDrawsFirst(history.value?.draws ?? []))
const errorMessage = computed(() => {
  if (!error.value) return null
  if (error.value instanceof HttpError && error.value.status === 404) {
    return 'There is no stored history for this game'
  }
  if (error.value instanceof HttpError && error.value.status === 503) {
    return 'Game history is unavailable right now. Try again shortly.'
  }
  return 'Could not load the game history'
})

const REASONS = {
  full_house: 'The full house was claimed.',
  host: 'The host ended the game.',
}

onMounted(() => {
  void run(() => fetchGameHistory(props.code))
})
</script>

<template>
  <section class="space-y-5">
    <h2 class="text-2xl font-bold">Game {{ code }}</h2>
    <p v-if="errorMessage" class="alert alert-error" role="alert">{{ errorMessage }}</p>
    <template v-else-if="history">
      <p class="alert">
        {{ REASONS[history.reason] }}
        <span v-if="history.pool_name">Pool: {{ history.pool_name }}</span>
      </p>
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Winners</h3>
          <ul class="space-y-2">
            <li v-for="entry in history.winners" :key="entry.prize" class="rounded-box bg-base-200 p-3 break-words" data-test="winner">
              {{ PRIZE_LABELS[entry.prize] }}:
              {{ entry.awarded_to.length ? entry.awarded_to.join(', ') : 'nobody' }}
            </li>
          </ul>
        </div>
      </div>
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Draws</h3>
          <p v-if="history.draws.length === 0">Nothing was drawn.</p>
          <ol v-else reversed class="space-y-2">
            <li v-for="draw in latestDraws" :key="draw.position" class="rounded-box bg-base-200 p-3 break-words" data-test="draw">
              {{ draw.position }}. {{ draw.name }}: {{ draw.explanation }}
            </li>
          </ol>
        </div>
      </div>
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Claims</h3>
          <p v-if="history.claims.length === 0">No claims were made.</p>
          <ol v-else class="space-y-2">
            <li v-for="(claim, index) in history.claims" :key="index" class="rounded-box bg-base-200 p-3 break-words" data-test="claim">
              {{ claim.player }} claimed {{ PRIZE_LABELS[claim.prize] }}:
              {{ claim.accepted ? 'accepted' : `refused. ${claim.error ? messageFor(claim.error) : ''}` }}
            </li>
          </ol>
        </div>
      </div>
    </template>
    <p v-else>Loading the game history...</p>
  </section>
</template>
