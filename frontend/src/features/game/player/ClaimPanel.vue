<script setup lang="ts">
import type { PrizeBoardEntry } from '../../../realtime/protocol'
import { PRIZE_LABELS, type Prize } from '../shared/prizes'

const props = defineProps<{ prizes: readonly PrizeBoardEntry[]; pending: readonly Prize[] }>()
defineEmits<{ claim: [prize: Prize] }>()

const isPending = (prize: Prize) => props.pending.includes(prize)
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Claim</h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="{ prize, awarded_to } in prizes"
          :key="prize"
          type="button"
          class="btn btn-outline"
          :data-test="`claim-${prize}`"
          :disabled="awarded_to.length > 0 || isPending(prize)"
          @click="$emit('claim', prize)"
        >{{ isPending(prize) ? 'Claiming' : 'Claim' }} {{ PRIZE_LABELS[prize] }}{{ isPending(prize) ? '…' : '' }}</button>
      </div>
    </div>
  </section>
</template>
