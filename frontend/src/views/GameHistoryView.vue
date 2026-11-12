<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { newestDrawsFirst } from '../draws'
import { PRIZE_LABELS } from '../prizes'
import { useHistoryStore } from '../stores/history'
import { messageFor } from '../stores/session'

const props = defineProps<{ code: string }>()
const store = useHistoryStore()
const latestDraws = computed(() => newestDrawsFirst(store.history?.draws ?? []))

const REASONS = {
  full_house: 'The full house was claimed.',
  host: 'The host ended the game.',
}

onMounted(() => {
  store.load(props.code)
})
</script>

<template>
  <section class="space-y-5">
    <h2 class="text-2xl font-bold">Game {{ code }}</h2>
    <p v-if="store.error" class="alert alert-error" role="alert">{{ store.error }}</p>
    <template v-else-if="store.history">
      <p class="alert">
        {{ REASONS[store.history.reason] }}
        <span v-if="store.history.pool_name">Pool: {{ store.history.pool_name }}</span>
      </p>
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Winners</h3>
          <ul class="space-y-2">
            <li v-for="entry in store.history.winners" :key="entry.prize" class="rounded-box bg-base-200 p-3 break-words" data-test="winner">
              {{ PRIZE_LABELS[entry.prize] }}:
              {{ entry.awarded_to.length ? entry.awarded_to.join(', ') : 'nobody' }}
            </li>
          </ul>
        </div>
      </div>
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <h3 class="card-title">Draws</h3>
          <p v-if="store.history.draws.length === 0">Nothing was drawn.</p>
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
          <p v-if="store.history.claims.length === 0">No claims were made.</p>
          <ol v-else class="space-y-2">
            <li v-for="(claim, index) in store.history.claims" :key="index" class="rounded-box bg-base-200 p-3 break-words" data-test="claim">
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
