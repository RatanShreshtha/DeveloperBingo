<script setup lang="ts">
import { ICONS, type IconName } from './icons'

// Decorative: the text beside an icon says what the control does, so the icon is hidden from
// assistive technology.
defineProps<{ name: IconName }>()
</script>

<template>
  <svg
    class="size-5 shrink-0"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <component
      :is="shape.tag"
      v-for="(shape, index) in ICONS[name]"
      :key="index"
      v-bind="shape.attrs"
    />
  </svg>
</template>
