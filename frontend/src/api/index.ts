import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginPage = window.location.pathname === '/login' || window.location.pathname === '/register'
    
    if (error.response?.status === 401 && !isLoginPage) {
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
    } else if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('网络错误，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export const bangumiApi = {
  getCalendar: (dataSource: string = 'mikan', year?: number, season?: string) =>
    api.get('/bangumi/calendar', { params: { data_source: dataSource, ...(year != null ? { year } : {}), ...(season ? { season } : {}) } }),
  getBangumi: (id: number) => api.get(`/bangumi/${id}`),
  getEpisodes: (id: number, maxPage: number = 3) => api.get(`/bangumi/${id}/episodes`, { params: { max_page: maxPage } }),
  search: (keyword: string, dataSource: string = 'mikan') => api.get('/bangumi/search', { params: { keyword, data_source: dataSource } }),
  refresh: (dataSource: string = 'mikan', year?: number, season?: string) =>
    api.post('/bangumi/refresh', null, { params: { data_source: dataSource, ...(year != null ? { year } : {}), ...(season ? { season } : {}) } }),
  refreshEpisodes: (id: number, dataSource: string = 'mikan') => api.post(`/bangumi/${id}/refresh-episodes`, null, { params: { data_source: dataSource } }),
}

export const subscriptionApi = {
  getAll: () => api.get('/subscriptions'),
  create: (data: {
    bangumi_id: number
    filter_mode?: 'inherit' | 'custom'
    include_keywords?: string
    exclude_keywords?: string
    subtitle_groups?: string
    language?: string
    regex_pattern?: string
    min_episode?: number
    max_episode?: number
  } & Record<string, unknown>) =>
    api.post('/subscriptions', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/subscriptions/${id}`, data),
  delete: (id: number) => api.delete(`/subscriptions/${id}`),
  // 当前生效的过滤规则来源与命中剧集（判定只由后端实现，前端不再复制一套）
  filtering: (id: number) => api.get(`/subscriptions/${id}/filtering`),
  getFilter: (id: number) => api.get(`/subscriptions/${id}/filter`),
  createFilter: (id: number, data: Record<string, unknown>) => api.post(`/subscriptions/${id}/filter`, data),
  updateFilter: (id: number, data: Record<string, unknown>) => api.put(`/subscriptions/${id}/filter`, data),
  deleteFilter: (id: number) => api.delete(`/subscriptions/${id}/filter`),
}

// 投放方式只有 RSS：服务器出 feed，用户自己的下载器按间隔拉取（详见 documents/auto-download-redesign.md）
export const rssApi = {
  subscriptionFeedUrl: (subscriptionId: number) => `/api/rss/subscription/${subscriptionId}`,
  regenerateSubscriptionToken: (subscriptionId: number) =>
    api.post(`/rss/subscription/${subscriptionId}/regenerate`),
}

export const authApi = {
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData)
  },
  register: (data: { username: string; email: string; password: string }) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  getRegistrationConfig: () => api.get('/auth/registration-config'),
}

export const userApi = {
  getMe: () => api.get('/users/me'),
  changePassword: (oldPassword: string, newPassword: string) =>
    api.put('/users/me/password', null, { params: { old_password: oldPassword, new_password: newPassword } }),
  getGlobalFilter: () => api.get('/users/me/global-filter'),
  createGlobalFilter: (data: Record<string, unknown>) => api.post('/users/me/global-filter', data),
  updateGlobalFilter: (data: Record<string, unknown>) => api.put('/users/me/global-filter', data),
  deleteGlobalFilter: () => api.delete('/users/me/global-filter'),
  getRssToken: () => api.get('/users/me/rss-token'),
  regenerateRssToken: () => api.post('/users/me/rss-token'),
}

export const settingsApi = {
  getSystem: () => api.get('/settings/system'),
  updateSystem: (data: Record<string, unknown>) => api.put('/settings/system', data),
}
