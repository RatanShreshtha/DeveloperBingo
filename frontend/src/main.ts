import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import { createRouter } from './router'

createApp(App).use(createPinia()).use(createRouter()).mount('#app')
