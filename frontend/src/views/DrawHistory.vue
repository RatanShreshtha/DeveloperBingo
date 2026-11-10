<script setup lang="ts">
import type { DrawnTopic } from '../realtime/socket'

defineProps<{ draws: DrawnTopic[] }>()
</script>

<template>
  <section>
    <h2>Draws</h2>
    <ol v-if="draws.length" data-test="draw-history">
      <li v-for="draw in draws" :key="draw.position">
        <strong>{{ draw.name }}</strong>: {{ draw.explanation }}
      </li>
    </ol>
    <p v-else>No topics drawn yet.</p>
  </section>
</template>
