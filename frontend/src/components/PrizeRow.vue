<script setup lang="ts">
import { PRIZE_LABELS, type Prize, type PrizeStatus } from '../utils/prizes'

defineProps<{ prize: Prize; outcome: string; status: PrizeStatus }>()

// Green once awarded, red when the game ended without it, grey while it can still be won.
const tone: Record<PrizeStatus, string> = {
  awarded: 'border-success bg-success/15',
  unavailable: 'border-error bg-error/15',
  open: 'border-base-300 bg-base-200',
}
</script>

<template>
  <li class="rounded-box border-l-4 p-3 break-words" :class="tone[status]">
    {{ PRIZE_LABELS[prize] }}: {{ outcome }}
  </li>
</template>
