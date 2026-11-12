import { createMemoryHistory } from 'vue-router'
import { createApplicationPlugins } from '../main'
import { createRouter } from '../router'

export function makeRouter() {
  return createRouter(createMemoryHistory())
}

export function makePlugins() {
  return [makeApplicationPlugins()]
}

export function makeApplicationPlugins() {
  return createApplicationPlugins(createMemoryHistory())
}
