<script setup lang="ts">
import { PRIZE_LABELS } from '../prizes'
import type { ClaimLogEntry, ErrorCode } from '../realtime/protocol'

defineProps<{ claims: ClaimLogEntry[]; messageFor: (code: ErrorCode) => string }>()
</script>

<template>
  <section>
    <h2>Claims</h2>
    <p v-if="claims.length === 0">No claims yet.</p>
    <ol v-else>
      <li v-for="(claim, index) in claims" :key="index" data-test="claim">
        {{ claim.player }} claimed {{ PRIZE_LABELS[claim.prize] }}:
        {{ claim.accepted ? 'accepted' : `refused. ${claim.error ? messageFor(claim.error) : ''}` }}
      </li>
    </ol>
  </section>
</template>
