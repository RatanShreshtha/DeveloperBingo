<script setup lang="ts">
import { PRIZE_LABELS } from '../prizes'
import type { PrizeBoardEntry } from '../realtime/protocol'

defineProps<{ prizes: PrizeBoardEntry[] }>()
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Prizes</h2>
      <ul class="space-y-2">
        <li v-for="entry in prizes" :key="entry.prize" class="rounded-box bg-base-200 p-3 break-words">
          {{ PRIZE_LABELS[entry.prize] }}:
          {{ entry.awarded_to.length ? `awarded to ${entry.awarded_to.join(', ')}` : 'still open' }}
        </li>
      </ul>
    </div>
  </section>
</template>
