<script setup lang="ts">
import HealthStatus from './HealthStatus.vue'
</script>

<template>
  <footer class="mx-auto max-w-7xl space-y-2 px-4 pb-8 sm:px-6 lg:px-8">
    <HealthStatus />
    <p class="text-sm text-base-content/70">
      &copy; {{ new Date().getFullYear() }} DeveloperBingo
    </p>
  </footer>
</template>
