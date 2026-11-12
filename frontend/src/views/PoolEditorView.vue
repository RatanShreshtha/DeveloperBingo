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
  <section>
    <h2>New custom pool</h2>
    <p><RouterLink to="/">Back to home</RouterLink></p>
    <p v-if="loadFailed" role="alert">Could not load the default pool to copy.</p>
    <template v-if="topics">
      <p>
        Copied from the default pool. Edit any topic, keeping 90 distinct topics that each have an
        explanation.
      </p>
      <label>
        Pool name
        <input v-model="name" type="text" data-test="pool-name" />
      </label>
      <ol>
        <li v-for="(topic, index) in topics" :key="index">
          <input v-model="topic.name" type="text" data-test="topic-name" aria-label="Topic name" />
          <input
            v-model="topic.explanation"
            type="text"
            data-test="topic-explanation"
            aria-label="Topic explanation"
          />
        </li>
      </ol>
      <button type="button" data-test="save-pool" @click="save">Save pool</button>
      <p v-if="refusal" role="alert">{{ refusal }}</p>
      <p v-if="failed" role="alert">Could not save the pool. Please try again.</p>
      <p v-if="saved">Saved. Pick it when you create a game.</p>
    </template>
  </section>
</template>
