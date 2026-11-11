<script setup lang="ts">
import { PRIZE_LABELS } from '../prizes'
import type { PrizeBoardEntry } from '../realtime/socket'

defineProps<{ prizes: PrizeBoardEntry[] }>()
</script>

<template>
  <section>
    <h2>Prizes</h2>
    <ul>
      <li v-for="entry in prizes" :key="entry.prize">
        {{ PRIZE_LABELS[entry.prize] }}:
        {{ entry.awarded_to.length ? `awarded to ${entry.awarded_to.join(', ')}` : 'still open' }}
      </li>
    </ul>
  </section>
</template>
