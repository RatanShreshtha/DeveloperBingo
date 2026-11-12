import { createPinia } from 'pinia'
import { createApp, type App as VueApp } from 'vue'
import type { RouterHistory } from 'vue-router'
import App from './App.vue'
import { createRouter } from './router'

export function createApplicationPlugins(history?: RouterHistory) {
  const pinia = createPinia()
  const router = createRouter(history)
  return {
    pinia,
    router,
    install(app: VueApp) {
      app.use(pinia)
      app.use(router)
    },
  }
}

export function createApplication(history?: RouterHistory) {
  const plugins = createApplicationPlugins(history)
  const app = createApp(App)
  app.use(plugins)
  return { app, pinia: plugins.pinia, router: plugins.router }
}
