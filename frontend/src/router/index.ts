import {
  createRouter as createVueRouter,
  createWebHistory,
  type RouterHistory,
  type RouteRecordRaw,
} from 'vue-router'

/** The host's private address for a game. The `/host/:code` route reads the token back from it. */
export function hostPath(link: { code: string; host_token: string }): string {
  return `/host/${encodeURIComponent(link.code)}?token=${encodeURIComponent(link.host_token)}`
}

export const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('../views/HomePage.vue') },
  {
    path: '/about',
    component: () => import('../views/AboutView.vue'),
    meta: { title: 'About' },
  },
  {
    path: '/rules',
    component: () => import('../views/RulesView.vue'),
    meta: { title: 'Rules' },
  },
  {
    path: '/join',
    component: () => import('../views/JoinPage.vue'),
    meta: { title: 'Join a game' },
  },
  {
    path: '/pools/new',
    component: () => import('../views/PoolEditorPage.vue'),
    meta: { title: 'New custom pool' },
  },
  {
    path: '/games/:code/history',
    component: () => import('../views/GameHistoryPage.vue'),
    meta: { title: 'Game history' },
    props: true,
  },
  {
    path: '/games/:code',
    component: () => import('../views/PlayerPage.vue'),
    meta: { title: 'Your game' },
    props: true,
  },
  {
    path: '/host/:code',
    component: () => import('../views/HostPage.vue'),
    props: (route) => ({ code: route.params.code, token: route.query.token }),
    meta: { title: 'Host dashboard' },
  },
]

export function createRouter(history: RouterHistory = createWebHistory()) {
  const router = createVueRouter({ history, routes })
  router.afterEach((to) => {
    const title = to.meta.title as string | undefined
    document.title = title ? `${title} · DeveloperBingo` : 'DeveloperBingo'
  })
  return router
}
