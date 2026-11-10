<script setup lang="ts">
import { RouterView } from 'vue-router'
import HealthView from './components/HealthView.vue'
</script>

<template>
  <main>
    <h1>DeveloperBingo</h1>
    <RouterView />
    <footer>
      <HealthView />
    </footer>
  </main>
</template>
