import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../router'

export function makeRouter() {
  return createRouter({ history: createMemoryHistory(), routes })
}

export function makePlugins() {
  return [createPinia(), makeRouter()]
}
