<script setup lang="ts">
import { PRIZE_LABELS } from '../utils/prizes'

const prizeDescriptions = [
  ['early_five', 'The first player to have any five topics ticked, wherever they sit on the ticket.'],
  ['top_line', 'Every topic in the top line of a ticket ticked.'],
  ['middle_line', 'Every topic in the middle line of a ticket ticked.'],
  ['bottom_line', 'Every topic in the bottom line of a ticket ticked.'],
  ['four_corners', 'The outermost topic in the top line and in the bottom line, on each side of the ticket.'],
  ['full_house', 'Every topic on a ticket ticked.'],
] as const
</script>

<template>
  <section class="mx-auto max-w-2xl space-y-6">
    <div class="space-y-2">
      <h2 class="text-3xl font-bold">Rules</h2>
      <p class="text-base-content/70">How a game is played and how prizes are won.</p>
    </div>
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body space-y-2">
        <h3 class="card-title">Playing</h3>
        <ul class="list-disc space-y-1 pl-5">
          <li>The host draws topics from the pool. A topic is drawn at most once per game.</li>
          <li>Each player's ticket holds topics from the pool. When a topic is drawn and is on your ticket, tick it.</li>
          <li>When you think you have won a prize, make a claim. Claims are checked against the draws.</li>
          <li>If several valid claims arrive for the same prize shortly after each other, they all win it together.</li>
          <li>The game ends when the full house is awarded, or when the host ends it.</li>
        </ul>
      </div>
    </div>
    <div class="card bg-base-100 shadow-sm">
      <div class="card-body space-y-2">
        <h3 class="card-title">Prizes</h3>
        <p>Each prize can be awarded at most once per game.</p>
        <dl class="space-y-2">
          <div v-for="[prize, description] in prizeDescriptions" :key="prize">
            <dt class="font-medium">{{ PRIZE_LABELS[prize] }}</dt>
            <dd class="text-base-content/80">{{ description }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>
