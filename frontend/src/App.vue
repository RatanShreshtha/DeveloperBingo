<script setup lang="ts">
import { RouterView } from 'vue-router'
import HealthStatus from './shared/ui/HealthStatus.vue'
</script>

<template>
  <div class="min-h-screen bg-base-200 text-base-content">
    <header class="border-b border-base-300 bg-base-100">
      <div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <h1 class="text-xl font-bold tracking-tight sm:text-2xl">DeveloperBingo</h1>
      </div>
    </header>
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <RouterView />
    </main>
    <footer class="mx-auto max-w-7xl px-4 pb-8 sm:px-6 lg:px-8">
      <HealthStatus />
    </footer>
  </div>
</template>
