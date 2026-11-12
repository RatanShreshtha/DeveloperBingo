<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDefaultPool, PoolRefusedError, savePool, type TopicResponse } from '../api/pools'

const name = ref('')
const topics = ref<TopicResponse[] | null>(null)
const loadFailed = ref(false)
const refusal = ref<string | null>(null)
const failed = ref(false)
const saved = ref(false)

onMounted(async () => {
  try {
    const pool = await fetchDefaultPool()
    topics.value = pool.columns.flat().map((topic) => ({ ...topic }))
  } catch {
    loadFailed.value = true
  }
})

async function save() {
  refusal.value = null
  failed.value = false
  saved.value = false
  try {
    await savePool(name.value, topics.value ?? [])
    saved.value = true
  } catch (error) {
    if (error instanceof PoolRefusedError) {
      refusal.value = error.message
    } else {
      failed.value = true
    }
  }
}
</script>

<template>
  <section class="space-y-5">
    <div class="space-y-2">
      <h2 class="text-2xl font-bold">New custom pool</h2>
      <p><RouterLink class="link" to="/">Back to home</RouterLink></p>
    </div>
    <p v-if="loadFailed" class="alert alert-error" role="alert">Could not load the default pool to copy.</p>
    <template v-if="topics">
      <div class="card bg-base-100 shadow-sm">
        <div class="card-body">
          <p>
            Copied from the default pool. Edit any topic, keeping 90 distinct topics that each have an
            explanation.
          </p>
          <label class="block max-w-lg space-y-2">
            <span class="font-medium">Pool name</span>
            <input v-model="name" class="input input-bordered w-full" type="text" data-test="pool-name" />
          </label>
          <ol class="space-y-3">
            <li v-for="(topic, index) in topics" :key="index" class="grid gap-2 rounded-box bg-base-200 p-3 sm:grid-cols-[3rem_minmax(0,1fr)_minmax(0,2fr)] sm:items-center">
              <span class="font-medium text-base-content/70">{{ index + 1 }}.</span>
              <input
                v-model="topic.name"
                class="input input-bordered w-full min-w-0"
                type="text"
                data-test="topic-name"
                :aria-label="`Topic ${index + 1} name`"
              />
              <input
                v-model="topic.explanation"
                class="input input-bordered w-full min-w-0"
                type="text"
                data-test="topic-explanation"
                :aria-label="`Topic ${index + 1} explanation`"
              />
            </li>
          </ol>
          <div class="card-actions">
            <button class="btn btn-primary dark:btn-neutral" type="button" data-test="save-pool" @click="save">Save pool</button>
          </div>
          <p v-if="refusal" class="alert alert-error" role="alert">{{ refusal }}</p>
          <p v-if="failed" class="alert alert-error" role="alert">Could not save the pool. Please try again.</p>
          <p v-if="saved" class="alert alert-success">Saved. Pick it when you create a game.</p>
        </div>
      </div>
    </template>
  </section>
</template>
