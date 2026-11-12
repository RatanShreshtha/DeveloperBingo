<script setup lang="ts">
import { onMounted } from 'vue'
import { PRIZE_LABELS } from '../prizes'
import { useHistoryStore } from '../stores/history'
import { messageFor } from '../stores/session'

const props = defineProps<{ code: string }>()
const store = useHistoryStore()

const REASONS = {
  full_house: 'The full house was claimed.',
  host: 'The host ended the game.',
}

onMounted(() => {
  store.load(props.code)
})
</script>

<template>
  <section>
    <h1>Game {{ code }}</h1>
    <p v-if="store.error" role="alert">{{ store.error }}</p>
    <template v-else-if="store.history">
      <p>
        {{ REASONS[store.history.reason] }}
        <span v-if="store.history.pool_name">Pool: {{ store.history.pool_name }}</span>
      </p>
      <h2>Winners</h2>
      <ul>
        <li v-for="entry in store.history.winners" :key="entry.prize" data-test="winner">
          {{ PRIZE_LABELS[entry.prize] }}:
          {{ entry.awarded_to.length ? entry.awarded_to.join(', ') : 'nobody' }}
        </li>
      </ul>
      <h2>Draws</h2>
      <p v-if="store.history.draws.length === 0">Nothing was drawn.</p>
      <ol v-else>
        <li v-for="draw in store.history.draws" :key="draw.position" data-test="draw">
          {{ draw.position }}. {{ draw.name }}: {{ draw.explanation }}
        </li>
      </ol>
      <h2>Claims</h2>
      <p v-if="store.history.claims.length === 0">No claims were made.</p>
      <ol v-else>
        <li v-for="(claim, index) in store.history.claims" :key="index" data-test="claim">
          {{ claim.player }} claimed {{ PRIZE_LABELS[claim.prize] }}:
          {{ claim.accepted ? 'accepted' : `refused. ${claim.error ? messageFor(claim.error) : ''}` }}
        </li>
      </ol>
    </template>
    <p v-else>Loading the game history...</p>
  </section>
</template>
