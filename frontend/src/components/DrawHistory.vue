<script setup lang="ts">
import { computed } from 'vue'
import { newestDrawsFirst } from '../utils/draws'
import type { DrawnTopic } from '../realtime/protocol'
import BoardCard from './BoardCard.vue'
import DrawItem from './DrawItem.vue'

const props = defineProps<{ draws: DrawnTopic[] }>()
const latestDraws = computed(() => newestDrawsFirst(props.draws))
</script>

<template>
  <BoardCard title="Draws">
    <ol v-if="latestDraws.length" class="space-y-2" data-test="draw-history">
      <DrawItem v-for="draw in latestDraws" :key="draw.position" :draw="draw" />
    </ol>
    <p v-else class="text-base-content/70">No topics drawn yet.</p>
  </BoardCard>
</template>
