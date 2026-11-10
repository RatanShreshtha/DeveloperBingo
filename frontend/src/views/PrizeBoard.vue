<script setup lang="ts">
import type { PrizeBoard } from '../realtime/socket'

defineProps<{ prizes: PrizeBoard }>()

// The words a player reads for each prize. Keys match the prize names the server sends.
const LABELS: Record<string, string> = {
  early_five: 'Early five',
}

function label(prize: string): string {
  return LABELS[prize] ?? prize
}
</script>

<template>
  <section>
    <h2>Prizes</h2>
    <ul>
      <li v-for="(winner, prize) in prizes" :key="prize">
        {{ label(prize) }}: {{ winner ? `won by ${winner}` : 'still open' }}
      </li>
    </ul>
  </section>
</template>
