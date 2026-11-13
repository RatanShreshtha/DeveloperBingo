<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header class="border-b border-base-300 bg-base-100">
    <div
      class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8"
    >
      <RouterLink to="/" class="text-xl font-bold tracking-tight sm:text-2xl"
        >DeveloperBingo</RouterLink
      >
      <nav class="flex gap-4 text-sm font-medium" aria-label="Main">
        <RouterLink to="/rules" class="link link-hover">Rules</RouterLink>
        <RouterLink to="/about" class="link link-hover">About</RouterLink>
      </nav>
    </div>
  </header>
</template>
