<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppFooter from './components/AppFooter.vue'
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col bg-base-200 text-base-content">
    <a
      href="#main-content"
      class="btn btn-primary sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50"
      >Skip to content</a
    >
    <AppHeader />
    <main
      id="main-content"
      tabindex="-1"
      class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8"
    >
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>
