<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { currentTheme, setTheme, type Theme } from '../theme'
import AppIcon from './AppIcon.vue'

const theme = ref<Theme>(currentTheme())

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  setTheme(theme.value)
}
</script>

<template>
  <header class="border-b border-base-300 bg-base-100 shadow-sm">
    <!-- On a phone the brand and the links take a row each; from `sm` they share one row. -->
    <div
      class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 px-4 py-1 sm:flex-nowrap sm:px-6 sm:py-3 lg:px-8"
    >
      <RouterLink
        to="/"
        class="inline-flex min-h-11 items-center text-lg font-bold tracking-tight text-primary sm:text-2xl"
        >DeveloperBingo</RouterLink
      >
      <nav
        class="flex flex-wrap items-center gap-x-1 text-sm font-medium"
        aria-label="Main"
      >
        <RouterLink
          to="/rules"
          class="link link-hover inline-flex min-h-11 items-center gap-2 px-3"
        >
          <AppIcon name="book" />Rules</RouterLink
        >
        <RouterLink
          to="/about"
          class="link link-hover inline-flex min-h-11 items-center gap-2 px-3"
        >
          <AppIcon name="info" />About</RouterLink
        >
        <button
          type="button"
          class="btn btn-soft min-h-11 gap-2 px-3"
          data-test="theme-toggle"
          @click="toggleTheme"
        >
          <AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" />
          {{ theme === 'dark' ? 'Light mode' : 'Dark mode' }}
        </button>
      </nav>
    </div>
  </header>
</template>
