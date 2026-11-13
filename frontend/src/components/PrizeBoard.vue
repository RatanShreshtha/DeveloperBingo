<script setup lang="ts">
import type { PrizeBoardEntry } from '../realtime/protocol'
import BoardCard from './BoardCard.vue'
import PrizeRow from './PrizeRow.vue'

defineProps<{ prizes: PrizeBoardEntry[] }>()
</script>

<template>
  <BoardCard title="Prizes">
    <ul class="space-y-2">
      <PrizeRow
        v-for="entry in prizes"
        :key="entry.prize"
        :prize="entry.prize"
        :outcome="
          entry.awarded_to.length
            ? `awarded to ${entry.awarded_to.join(', ')}`
            : 'still open'
        "
      />
    </ul>
  </BoardCard>
</template>
