<script setup lang="ts">
withDefaults(defineProps<{ title: string; heading?: 'h2' | 'h3' }>(), { heading: 'h2' })
</script>

<template>
  <section class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <component :is="heading" class="card-title">{{ title }}</component>
      <slot />
    </div>
  </section>
</template>
