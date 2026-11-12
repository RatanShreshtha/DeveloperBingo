<script setup lang="ts">
import type { TopicResponse } from '../api/pools'

defineProps<{ columns: TopicResponse[][] }>()
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Pool</h2>
      <div class="pool-columns grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="(column, index) in columns" :key="index" class="pool-column min-w-0 rounded-box bg-base-200 p-4">
          <h3 class="font-semibold">Column {{ index + 1 }}</h3>
          <ul class="mt-2 space-y-2">
            <li v-for="topic in column" :key="topic.name" class="break-words">
              <strong>{{ topic.name }}</strong>: {{ topic.explanation }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
