<script setup lang="ts">
import { onMounted } from 'vue'
import { useLobbyStore } from '../stores/lobby'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'

const props = defineProps<{ code: string }>()
const store = useLobbyStore()

onMounted(() => {
  store.loadDrawHistory(props.code)
})
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <p v-if="store.started">The game has started.</p>
    <p v-else>Waiting for the host to start the game.</p>
    <table v-if="store.ticket" class="ticket" aria-label="Your ticket">
      <tbody>
        <tr v-for="(line, lineIndex) in store.ticket" :key="lineIndex">
          <td
            v-for="(cell, columnIndex) in line"
            :key="columnIndex"
            data-test="ticket-cell"
          >{{ cell ?? '' }}</td>
        </tr>
      </tbody>
    </table>
    <DrawHistory :draws="store.draws" />
    <LobbyList :players="store.players" />
  </section>
</template>
