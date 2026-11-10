import { createRouter as createVueRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from './views/HomeView.vue'
import JoinView from './views/JoinView.vue'
import HostView from './views/HostView.vue'
import PlayerLobbyView from './views/PlayerLobbyView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', component: HomeView },
  { path: '/join', component: JoinView },
  { path: '/games/:code', component: PlayerLobbyView, props: true },
  {
    path: '/host/:code',
    component: HostView,
    props: (route) => ({ code: route.params.code, token: route.query.token }),
  },
]

export function createRouter() {
  return createVueRouter({ history: createWebHistory(), routes })
}
