<script setup lang="ts">
import { PRIZE_LABELS } from '../shared/prizes'
import type { ClaimLogEntry, ErrorCode } from '../../../realtime/protocol'

defineProps<{ claims: ClaimLogEntry[]; messageFor: (code: ErrorCode) => string }>()
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Claims</h2>
      <p v-if="claims.length === 0" class="text-base-content/70">No claims yet.</p>
      <ol v-else class="space-y-2">
        <li v-for="(claim, index) in claims" :key="index" class="rounded-box bg-base-200 p-3 break-words" data-test="claim">
          {{ claim.player }} claimed {{ PRIZE_LABELS[claim.prize] }}:
          {{ claim.accepted ? 'accepted' : `refused. ${claim.error ? messageFor(claim.error) : ''}` }}
        </li>
      </ol>
    </div>
  </section>
</template>
