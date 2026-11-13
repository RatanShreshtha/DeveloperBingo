<script setup lang="ts">
import type { TopicResponse } from '../api/pools'
import BoardCard from './BoardCard.vue'

defineProps<{ columns: TopicResponse[][] }>()
</script>

<template>
  <BoardCard title="Pool">
    <div class="pool-columns grid gap-4 md:grid-cols-2 xl:grid-cols-3">
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
  </BoardCard>
</template>
