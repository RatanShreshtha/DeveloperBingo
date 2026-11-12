<script setup lang="ts">
import type { ClaimLogEntry } from '../realtime/protocol'
import BoardCard from './BoardCard.vue'
import ClaimItem from './ClaimItem.vue'

defineProps<{ claims: ClaimLogEntry[] }>()
</script>

<template>
  <BoardCard title="Claims">
    <p v-if="claims.length === 0" class="text-base-content/70">No claims yet.</p>
    <ol v-else class="space-y-2">
      <ClaimItem v-for="(claim, index) in claims" :key="index" :claim="claim" />
    </ol>
  </BoardCard>
</template>
