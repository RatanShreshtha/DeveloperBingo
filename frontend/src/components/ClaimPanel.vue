<script setup lang="ts">
import { useId } from 'vue'
import AppIcon from './AppIcon.vue'
import type { PrizeBoardEntry } from '../realtime/protocol'
import { PRIZE_LABELS, type Prize } from '../utils/prizes'

const props = defineProps<{
  prizes: readonly PrizeBoardEntry[]
  pending: readonly Prize[]
}>()
defineEmits<{ claim: [prize: Prize] }>()

const isPending = (prize: Prize) => props.pending.includes(prize)
const titleId = useId()
</script>

<template>
  <section class="card bg-base-100 shadow-sm" :aria-labelledby="titleId">
    <div class="card-body">
      <h2 :id="titleId" class="card-title">
        <AppIcon name="check" class="text-primary" />
        Claim
      </h2>
      <div
        class="flex gap-2 overflow-x-auto pb-1"
        role="group"
        aria-label="Claim a prize"
      >
        <button
          v-for="{ prize, awarded_to } in prizes"
          :key="prize"
          type="button"
          class="btn btn-soft shrink-0 whitespace-nowrap"
          :data-test="`claim-${prize}`"
          :disabled="awarded_to.length > 0 || isPending(prize)"
          @click="$emit('claim', prize)"
        >
          {{ isPending(prize) ? 'Claiming' : 'Claim' }} {{ PRIZE_LABELS[prize]
          }}{{ isPending(prize) ? '…' : '' }}
        </button>
      </div>
    </div>
  </section>
</template>
