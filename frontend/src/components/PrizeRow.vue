<script setup lang="ts">
import { PRIZE_LABELS, type Prize } from '../utils/prizes'

defineProps<{ prize: Prize; outcome: string }>()
</script>

<template>
  <li class="rounded-box bg-base-200 p-3 break-words">{{ PRIZE_LABELS[prize] }}: {{ outcome }}</li>
</template>
