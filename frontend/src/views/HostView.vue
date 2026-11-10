<script setup lang="ts">
import { onMounted } from 'vue'
import { useLobbyStore } from '../stores/lobby'
import LobbyList from './LobbyList.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useLobbyStore()

onMounted(() => {
  store.watchAsHost(props.code, props.token ?? '')
})
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.error" role="alert">{{ store.error }}</p>
    <LobbyList v-else :players="store.players" />
  </section>
</template>
