<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { fetchGameHistory, type GameHistoryResponse } from '../api/games'
import { HttpError } from '../api/request'
import { useAsyncState } from '../composables/useAsyncState'
import { newestDrawsFirst } from '../utils/draws'
import BoardCard from '../components/BoardCard.vue'
import ClaimItem from '../components/ClaimItem.vue'
import DrawItem from '../components/DrawItem.vue'
import PrizeRow from '../components/PrizeRow.vue'

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

const REASONS: Record<GameHistoryResponse['reason'], string> = {
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
      <BoardCard title="Winners" heading="h3">
        <ul class="space-y-2">
          <PrizeRow
            v-for="entry in history.winners"
            :key="entry.prize"
            :prize="entry.prize"
            :outcome="entry.awarded_to.length ? entry.awarded_to.join(', ') : 'nobody'"
            data-test="winner"
          />
        </ul>
      </BoardCard>
      <BoardCard title="Draws" heading="h3">
        <p v-if="history.draws.length === 0">Nothing was drawn.</p>
        <ol v-else class="space-y-2">
          <DrawItem v-for="draw in latestDraws" :key="draw.position" :draw="draw" data-test="draw" />
        </ol>
      </BoardCard>
      <BoardCard title="Claims" heading="h3">
        <p v-if="history.claims.length === 0">No claims were made.</p>
        <ol v-else class="space-y-2">
          <ClaimItem v-for="(claim, index) in history.claims" :key="index" :claim="claim" />
        </ol>
      </BoardCard>
    </template>
    <p v-else>Loading the game history...</p>
  </section>
</template>
