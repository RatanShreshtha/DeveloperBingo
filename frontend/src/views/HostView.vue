<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDefaultPool, type TopicResponse } from '../api/pools'
import { useLobbyStore } from '../stores/lobby'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'
import PoolColumns from './PoolColumns.vue'

const props = defineProps<{ code: string; token: string | undefined }>()
const store = useLobbyStore()
const pool = ref<TopicResponse[][] | null>(null)
const poolError = ref(false)

function hostToken(): string {
  return props.token ?? ''
}

onMounted(async () => {
  store.watchAsHost(props.code, hostToken())
  try {
    pool.value = (await fetchDefaultPool()).columns
  } catch {
    poolError.value = true
  }
})
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.error" role="alert">{{ store.error }}</p>
    <div v-if="!store.started">
      <button type="button" data-test="start-game" @click="store.start(code, hostToken())">
        Start game
      </button>
    </div>
    <div v-else>
      <button type="button" data-test="draw-topic" @click="store.drawNext(code, hostToken())">
        Draw topic
      </button>
    </div>
    <DrawHistory :draws="store.draws" />
    <LobbyList :players="store.players" />
    <PoolColumns v-if="pool" :columns="pool" />
    <p v-else-if="poolError" role="alert">Could not load the default pool.</p>
  </section>
</template>
