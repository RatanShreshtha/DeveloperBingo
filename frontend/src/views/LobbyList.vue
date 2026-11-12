<script setup lang="ts">
defineProps<{ players: string[] }>()
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">Lobby ({{ players.length }})</h2>
      <ul v-if="players.length" class="flex flex-wrap gap-2">
        <li v-for="player in players" :key="player" class="badge badge-outline h-auto max-w-full py-2 break-all">{{ player }}</li>
      </ul>
      <p v-else class="text-base-content/70">No players yet.</p>
    </div>
  </section>
</template>
