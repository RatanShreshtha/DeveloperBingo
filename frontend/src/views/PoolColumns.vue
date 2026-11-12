<script setup lang="ts">
import type { TopicResponse } from '../api/pools'

defineProps<{ columns: TopicResponse[][] }>()
</script>

<template>
  <section>
    <h2>Pool</h2>
    <div class="pool-columns">
      <div v-for="(column, index) in columns" :key="index" class="pool-column">
        <h3>Column {{ index + 1 }}</h3>
        <ul>
          <li v-for="topic in column" :key="topic.name">
            <strong>{{ topic.name }}</strong>: {{ topic.explanation }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
