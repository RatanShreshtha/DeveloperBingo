<script setup lang="ts">
import { useLobbyStore } from '../stores/lobby'
import LobbyList from './LobbyList.vue'

defineProps<{ code: string }>()
const store = useLobbyStore()
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <LobbyList :players="store.players" />
  </section>
</template>
