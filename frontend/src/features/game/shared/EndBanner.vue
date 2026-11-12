<script setup lang="ts">
import type { GameEnd } from '../../../realtime/protocol'
import { END_MESSAGES } from './endMessages'

defineProps<{ role: 'host' | 'player'; reason: GameEnd['reason']; code: string }>()
</script>

<template>
  <p class="alert alert-info">
    {{ END_MESSAGES[role][reason] }}
    <RouterLink class="link" :to="`/games/${code}/history`" data-test="history-link">View the game history</RouterLink>
  </p>
</template>
