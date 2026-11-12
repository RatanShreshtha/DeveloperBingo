import {
  createRouter as createVueRouter,
  createWebHistory,
  type RouterHistory,
  type RouteRecordRaw,
} from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('../views/HomePage.vue') },
  { path: '/about', component: () => import('../views/AboutView.vue') },
  { path: '/rules', component: () => import('../views/RulesView.vue') },
  { path: '/join', component: () => import('../views/JoinPage.vue') },
  { path: '/pools/new', component: () => import('../views/PoolEditorPage.vue') },
  { path: '/games/:code/history', component: () => import('../views/GameHistoryPage.vue'), props: true },
  { path: '/games/:code', component: () => import('../views/PlayerPage.vue'), props: true },
  {
    path: '/host/:code',
    component: () => import('../views/HostPage.vue'),
    props: (route) => ({ code: route.params.code, token: route.query.token }),
  },
]

export function createRouter(history: RouterHistory = createWebHistory()) {
  return createVueRouter({ history, routes })
}
