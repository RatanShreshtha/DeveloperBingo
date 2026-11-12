<script setup lang="ts">
import type { DrawnTopic } from '../realtime/protocol'

defineProps<{ draw: DrawnTopic }>()
</script>

<template>
  <li class="rounded-box bg-base-200 p-3 break-words">
    {{ draw.position }}. <strong>{{ draw.name }}</strong>: {{ draw.explanation }}
  </li>
</template>
