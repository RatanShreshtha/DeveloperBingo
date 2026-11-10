<script setup lang="ts">
import { useLobbyStore } from '../stores/lobby'
import DrawHistory from './DrawHistory.vue'
import LobbyList from './LobbyList.vue'

defineProps<{ code: string }>()
const store = useLobbyStore()
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
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
