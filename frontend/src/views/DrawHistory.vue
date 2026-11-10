<script setup lang="ts">
import type { DrawnTopic } from '../realtime/socket'

defineProps<{ draws: DrawnTopic[] }>()
</script>

<template>
  <section>
    <h2>Draws</h2>
    <template v-if="draws.length">
      <p>
        Latest: <strong>{{ draws[draws.length - 1].name }}</strong>.
        {{ draws[draws.length - 1].explanation }}
      </p>
      <ol data-test="draw-history">
        <li v-for="draw in draws" :key="draw.position">
          {{ draw.name }}
        </li>
      </ol>
    </template>
    <p v-else>No topics drawn yet.</p>
  </section>
</template>
