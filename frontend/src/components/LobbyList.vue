<script setup lang="ts">
import BoardCard from './BoardCard.vue'

defineProps<{ players: string[] }>()
</script>

<template>
  <BoardCard :title="`Lobby (${players.length})`" icon="users">
    <ul v-if="players.length" class="flex flex-wrap gap-2">
      <li
        v-for="player in players"
        :key="player"
        class="badge badge-outline h-auto max-w-full px-3 py-2 text-sm break-all"
      >
        {{ player }}
      </li>
    </ul>
    <p v-else class="text-base-content/70">No players yet.</p>
  </BoardCard>
</template>
