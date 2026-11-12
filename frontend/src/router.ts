import {
  createRouter as createVueRouter,
  createWebHistory,
  type RouterHistory,
  type RouteRecordRaw,
} from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('./features/home/HomePage.vue') },
  { path: '/join', component: () => import('./features/game/player/JoinPage.vue') },
  { path: '/pools/new', component: () => import('./features/pool/PoolEditorPage.vue') },
  { path: '/games/:code/history', component: () => import('./features/history/GameHistoryPage.vue'), props: true },
  { path: '/games/:code', component: () => import('./features/game/player/PlayerPage.vue'), props: true },
  {
    path: '/host/:code',
    component: () => import('./features/game/host/HostPage.vue'),
    props: (route) => ({ code: route.params.code, token: route.query.token }),
  },
]

export function createRouter(history: RouterHistory = createWebHistory()) {
  return createVueRouter({ history, routes })
}
