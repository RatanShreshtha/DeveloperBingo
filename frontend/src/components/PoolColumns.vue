<script setup lang="ts">
import { computed } from 'vue'
import type { TopicResponse } from '../api/pools'
import BoardCard from './BoardCard.vue'

const props = defineProps<{ columns: TopicResponse[][] }>()
// The whole pool is long reference material, so it starts folded: the host's screen stays on the game.
const topicCount = computed(() => props.columns.flat().length)
</script>

<template>
  <BoardCard title="Pool" icon="book">
    <details class="group">
      <summary class="link link-hover cursor-pointer text-sm font-medium">
        Show all {{ topicCount }} topics
      </summary>
      <div class="pool-columns mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="(column, index) in columns"
          :key="index"
          class="pool-column min-w-0 rounded-box bg-base-200 p-4"
        >
          <h3 class="font-semibold">Column {{ index + 1 }}</h3>
          <ul class="mt-2 space-y-2">
            <li v-for="topic in column" :key="topic.name" class="break-words">
              <strong>{{ topic.name }}</strong>: {{ topic.explanation }}
            </li>
          </ul>
        </div>
      </div>
    </details>
  </BoardCard>
</template>
