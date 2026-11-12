<script setup lang="ts">
import type { PlayerSnapshot } from '../../../realtime/protocol'

defineProps<{
  ticket: PlayerSnapshot['ticket']
  ticks: readonly string[]
  drawn: readonly string[]
  ended: boolean
}>()
defineEmits<{ toggle: [topic: string] }>()
</script>

<template>
  <div class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h3 class="card-title">Your ticket</h3>
      <p class="text-sm text-base-content/70 lg:hidden">Scroll sideways to see the full ticket.</p>
      <div class="overflow-x-auto" role="region" aria-label="Your ticket, scroll horizontally" tabindex="0">
        <table class="ticket w-full min-w-[48rem] table-fixed border-separate border-spacing-1" aria-label="Your ticket">
          <tbody>
            <tr v-for="(line, lineIndex) in ticket" :key="lineIndex">
              <td
                v-for="(cell, columnIndex) in line"
                :key="columnIndex"
                class="h-16 rounded-lg bg-base-200"
                data-test="ticket-cell"
              >
                <button
                  v-if="cell"
                  type="button"
                  class="btn btn-sm h-full min-h-16 w-full text-[0.6875rem] whitespace-normal break-words leading-tight disabled:!border-base-300 disabled:!bg-base-200 disabled:!text-base-content disabled:!opacity-100"
                  :class="ticks.includes(cell) ? 'btn-success text-black' : 'btn-outline'"
                  data-test="tick-cell"
                  :aria-pressed="ticks.includes(cell)"
                  :disabled="ended || !drawn.includes(cell)"
                  @click="$emit('toggle', cell)"
                >{{ cell }}<span v-if="ticks.includes(cell)" aria-hidden="true"> ✓</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
