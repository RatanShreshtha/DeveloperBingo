<script setup lang="ts">
import { useId } from 'vue'
import AppIcon from './AppIcon.vue'
import type { IconName } from './icons'

defineProps<{ title: string; icon?: IconName }>()

// The section is named by its heading, so screen readers can list it by name.
const titleId = useId()
</script>

<template>
  <section class="card bg-base-100 shadow-sm" :aria-labelledby="titleId">
    <div class="card-body">
      <h2 :id="titleId" class="card-title">
        <AppIcon v-if="icon" :name="icon" class="text-primary" />
        {{ title }}
      </h2>
      <slot />
    </div>
  </section>
</template>
