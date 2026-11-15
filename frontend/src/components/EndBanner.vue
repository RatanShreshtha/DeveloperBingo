<script setup lang="ts">
import type { GameEnd } from '../realtime/protocol'
import { END_MESSAGES } from '../utils/endMessages'
import AppIcon from './AppIcon.vue'

defineProps<{
  role: 'host' | 'player'
  reason: GameEnd['reason']
  code: string
}>()
</script>

<template>
  <p class="alert border-l-4 border-accent bg-base-100 shadow-sm">
    {{ END_MESSAGES[role][reason] }}
    <RouterLink
      class="link inline-flex items-center gap-2"
      :to="`/games/${code}/history`"
      data-test="history-link"
    >
      <AppIcon name="clock" />View the game history</RouterLink
    >
  </p>
</template>
