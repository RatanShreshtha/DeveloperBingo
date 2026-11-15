<script setup lang="ts">
import type { PrizeBoardEntry } from '../realtime/protocol'
import type { PrizeStatus } from '../utils/prizes'
import BoardCard from './BoardCard.vue'
import PrizeRow from './PrizeRow.vue'

withDefaults(defineProps<{ prizes: PrizeBoardEntry[]; ended?: boolean }>(), {
  ended: false,
})

function statusOf(entry: PrizeBoardEntry, ended: boolean): PrizeStatus {
  if (entry.awarded_to.length) return 'awarded'
  return ended ? 'unavailable' : 'open'
}
</script>

<template>
  <BoardCard title="Prizes" icon="trophy">
    <ul class="space-y-2">
      <PrizeRow
        v-for="entry in prizes"
        :key="entry.prize"
        :prize="entry.prize"
        :status="statusOf(entry, ended)"
        :outcome="
          entry.awarded_to.length
            ? `awarded to ${entry.awarded_to.join(', ')}`
            : ended
              ? 'not awarded'
              : 'still open'
        "
      />
    </ul>
  </BoardCard>
</template>
