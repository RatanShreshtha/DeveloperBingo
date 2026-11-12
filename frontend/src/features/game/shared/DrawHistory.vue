<script setup lang="ts">
import { computed } from 'vue'
import { newestDrawsFirst } from './draws'
import type { DrawnTopic } from '../../../realtime/protocol'

const props = defineProps<{ draws: DrawnTopic[] }>()
const latestDraws = computed(() => newestDrawsFirst(props.draws))
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Draws</h2>
      <ol v-if="latestDraws.length" reversed class="space-y-2" data-test="draw-history">
        <li v-for="draw in latestDraws" :key="draw.position" class="rounded-box bg-base-200 p-3 break-words">
          <strong>{{ draw.name }}</strong>: {{ draw.explanation }}
        </li>
      </ol>
      <p v-else class="text-base-content/70">No topics drawn yet.</p>
    </div>
  </section>
</template>
