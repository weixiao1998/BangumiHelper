import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresAuth: false },
    },
    {
      // RSS 条目 <link> 的落地页：在阅读器里点开时通常没有登录态，因此免认证
      path: '/episode/:id',
      name: 'EpisodeDetail',
      component: () => import('@/views/EpisodeDetail.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Home',
          component: () => import('@/views/Calendar.vue'),
        },
        {
          path: 'bangumi/:id',
          name: 'BangumiDetail',
          component: () => import('@/views/BangumiDetail.vue'),
        },
        {
          path: 'subscriptions',
          name: 'Subscriptions',
          component: () => import('@/views/Subscriptions.vue'),
        },
        {
          path: 'search',
          name: 'Search',
          component: () => import('@/views/Search.vue'),
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/Settings.vue'),
        },
      ],
    },
  ],
})

// vue-router 5 起 next() 回调已废弃（运行时会打 VUE_ROUTER_R0025），改用返回值：
// 返回 false 中止、返回 location 重定向、返回 undefined 放行
router.beforeEach((to) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'Login' || to.name === 'Register') && userStore.isLoggedIn) {
    return { name: 'Home' }
  }
})

export default router
