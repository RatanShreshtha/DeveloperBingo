<script setup lang="ts">
defineProps<{ title: string; code: string }>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <h2 class="text-2xl font-bold">{{ title }}</h2>
    <p class="badge badge-outline h-auto px-3 py-2">
      Game code: <strong class="ml-1">{{ code }}</strong>
    </p>
  </div>
</template>
