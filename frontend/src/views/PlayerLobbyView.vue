<script setup lang="ts">
import { useLobbyStore } from '../stores/lobby'
import LobbyList from './LobbyList.vue'

defineProps<{ code: string }>()
const store = useLobbyStore()
</script>

<template>
  <section>
    <p>Game code: <strong>{{ code }}</strong></p>
    <table v-if="store.ticket" class="ticket" aria-label="Your ticket">
      <tbody>
        <tr v-for="(row, rowIndex) in store.ticket" :key="rowIndex">
          <td
            v-for="(cell, columnIndex) in row"
            :key="columnIndex"
            data-test="ticket-cell"
          >{{ cell ?? '' }}</td>
        </tr>
      </tbody>
    </table>
    <LobbyList :players="store.players" />
  </section>
</template>
