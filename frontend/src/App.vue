<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppFooter from './components/AppFooter.vue'
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col bg-base-200 text-base-content">
    <main class="flex flex-1 flex-col">
      <AppHeader />
      <section class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <RouterView />
      </section>
      <AppFooter />
    </main>
  </div>
</template>
