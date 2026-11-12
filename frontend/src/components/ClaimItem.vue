<script setup lang="ts">
import { messageFor } from '../utils/errors'
import { PRIZE_LABELS } from '../utils/prizes'
import type { ClaimLogEntry } from '../realtime/protocol'

defineProps<{ claim: ClaimLogEntry }>()
</script>

<template>
  <li class="rounded-box bg-base-200 p-3 break-words" data-test="claim">
    {{ claim.player }} claimed {{ PRIZE_LABELS[claim.prize] }}:
    {{ claim.accepted ? 'accepted' : `refused. ${claim.error ? messageFor(claim.error) : ''}` }}
  </li>
</template>
