<script setup lang="ts">
import { EARLY_FIVE } from '../prizes'
import type { PrizeBoard } from '../realtime/socket'

defineProps<{ prizes: PrizeBoard }>()

// The words a player reads for each prize, keyed by the prize's wire name.
const LABELS: Record<string, string> = {
  [EARLY_FIVE]: 'Early five',
}

function label(prize: string): string {
  return LABELS[prize] ?? prize
}
</script>

<template>
  <section>
    <h2>Prizes</h2>
    <ul>
      <li v-for="(awardedTo, prize) in prizes" :key="prize">
        {{ label(prize) }}: {{ awardedTo ? `awarded to ${awardedTo}` : 'still open' }}
      </li>
    </ul>
  </section>
</template>
