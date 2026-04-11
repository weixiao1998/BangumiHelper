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
  getCalendar: (dataSource: string = 'mikan') => api.get('/bangumi/calendar', { params: { data_source: dataSource } }),
  getBangumi: (id: number) => api.get(`/bangumi/${id}`),
  getEpisodes: (id: number, maxPage: number = 3) => api.get(`/bangumi/${id}/episodes`, { params: { max_page: maxPage } }),
  search: (keyword: string, dataSource: string = 'mikan') => api.get('/bangumi/search', { params: { keyword, data_source: dataSource } }),
  refresh: (dataSource: string = 'mikan') => api.post('/bangumi/refresh', null, { params: { data_source: dataSource } }),
  refreshEpisodes: (id: number, dataSource: string = 'mikan') => api.post(`/bangumi/${id}/refresh-episodes`, null, { params: { data_source: dataSource } }),
}

export const subscriptionApi = {
  getAll: () => api.get('/subscriptions'),
  create: (data: { bangumi_id: number; auto_download?: boolean; downloader_id?: number; save_path?: string }) =>
    api.post('/subscriptions', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/subscriptions/${id}`, data),
  delete: (id: number) => api.delete(`/subscriptions/${id}`),
  mark: (id: number, episode: number) => api.post(`/subscriptions/${id}/mark`, null, { params: { episode } }),
  createFilter: (id: number, data: Record<string, unknown>) => api.post(`/subscriptions/${id}/filter`, data),
  updateFilter: (id: number, data: Record<string, unknown>) => api.put(`/subscriptions/${id}/filter`, data),
}

export const downloaderApi = {
  getAll: () => api.get('/downloaders'),
  create: (data: Record<string, unknown>) => api.post('/downloaders', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/downloaders/${id}`, data),
  delete: (id: number) => api.delete(`/downloaders/${id}`),
  test: (id: number) => api.post(`/downloaders/${id}/test`),
  download: (data: { episode_ids: number[]; downloader_id?: number; download_type?: string }) => 
    api.post('/downloaders/download', data),
  regenerateRssToken: (subscriptionId: number) => api.post(`/downloaders/rss/${subscriptionId}/regenerate`),
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
}
