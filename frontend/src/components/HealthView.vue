<script setup lang="ts">
import { onMounted } from 'vue'
import { useHealthStore } from '../stores/health'

const store = useHealthStore()

onMounted(() => {
  store.load()
})
</script>

<template>
  <section class="health">
    <p v-if="store.loading">Checking backend…</p>
    <p v-else-if="store.error" role="alert">{{ store.error }}</p>
    <template v-else-if="store.health">
      <p>Status: {{ store.health.status }}</p>
      <p>Database: {{ store.health.database }}</p>
    </template>
  </section>
</template>
