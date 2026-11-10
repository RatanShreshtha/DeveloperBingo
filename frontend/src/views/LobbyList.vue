<script setup lang="ts">
defineProps<{ players: string[] }>()
</script>

<template>
  <section>
    <h2>Lobby ({{ players.length }})</h2>
    <ul v-if="players.length">
      <li v-for="player in players" :key="player">{{ player }}</li>
    </ul>
    <p v-else>No players yet.</p>
  </section>
</template>
