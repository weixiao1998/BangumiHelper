<template>
  <div class="page-container">
    <el-page-header @back="router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">{{ bangumi?.name || '番剧详情' }}</span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="10" animated style="margin-top: 20px" />

    <template v-else-if="bangumi">
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="6">
          <el-image :src="bangumi.cover || '/placeholder.png'" fit="cover" style="width: 100%; border-radius: 8px" />
        </el-col>
        <el-col :span="18">
          <h2>{{ bangumi.name }}</h2>
          <p class="meta">
            <el-tag>更新: {{ bangumi.update_time }}</el-tag>
            <el-tag type="info">{{ bangumi.data_source }}</el-tag>
          </p>
          <p v-if="bangumi.description" class="description">{{ bangumi.description }}</p>

          <div class="actions">
            <el-button v-if="!isSubscribed" type="primary" @click="showSubscribeDialog = true">订阅</el-button>
            <el-button v-else type="danger" @click="handleUnsubscribe">取消订阅</el-button>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3 style="margin: 0;">剧集列表</h3>
        <el-button type="primary" :loading="refreshing" @click="handleRefreshEpisodes">
          刷新剧集
        </el-button>
      </div>
      <el-table :data="episodes" style="margin-top: 16px">
        <el-table-column prop="episode_number" label="集数" width="80" />
        <el-table-column prop="title" label="标题" min-width="250">
          <template #default="{ row }">
            <el-tooltip :content="row.title" placement="top">
              <span class="episode-title">{{ row.title }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="subtitle_group" label="字幕组" width="120" />
        <el-table-column label="发布时间" width="150">
          <template #default="{ row }">
            {{ row.publish_time ? dayjs(row.publish_time).format('YYYY-MM-DD HH:mm') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="下载" width="240" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.magnet_url" 
                size="small" 
                type="primary"
                @click="handleDownload(row, 'magnet')"
              >
                磁力下载
              </el-button>
              <el-button 
                v-if="row.torrent_url" 
                size="small"
                type="success"
                @click="handleDownload(row, 'torrent')"
              >
                种子下载
              </el-button>
              <el-button 
                v-if="!row.magnet_url && !row.torrent_url" 
                size="small" 
                disabled
              >
                无下载链接
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="showSubscribeDialog" title="订阅设置" width="500px">
      <el-form :model="subscribeForm" label-width="100px">
        <el-form-item label="自动下载">
          <el-switch v-model="subscribeForm.auto_download" />
        </el-form-item>
        <el-form-item v-if="subscribeForm.auto_download" label="下载器">
          <el-select v-model="subscribeForm.downloader_id" placeholder="选择下载器">
            <el-option v-for="d in downloaders" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="保存路径">
          <el-input v-model="subscribeForm.save_path" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSubscribeDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubscribe">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { bangumiApi, subscriptionApi, downloaderApi } from '@/api'

interface Episode {
  id: number
  title: string
  episode_number: number
  torrent_url: string | null
  magnet_url: string | null
  subtitle_group: string
  publish_time: string
}

interface Bangumi {
  id: number
  name: string
  cover: string
  update_time: string
  data_source: string
  description: string
  episodes: Episode[]
}

interface Downloader {
  id: number
  name: string
  downloader_type: string
  host: string
  port: number
  is_default: boolean
}

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const refreshing = ref(false)
const bangumi = ref<Bangumi | null>(null)
const episodes = ref<Episode[]>([])
const isSubscribed = ref(false)
const subscriptionId = ref<number | null>(null)
const downloaders = ref<Downloader[]>([])

const showSubscribeDialog = ref(false)
const subscribeForm = ref({
  auto_download: false,
  downloader_id: null as number | null,
  save_path: '',
})

const bangumiId = computed(() => Number(route.params.id))

async function fetchBangumi() {
  loading.value = true
  try {
    const response = await bangumiApi.getBangumi(bangumiId.value)
    bangumi.value = response.data
    episodes.value = response.data.episodes || []

    const subResponse = await subscriptionApi.getAll()
    const sub = subResponse.data.find((s: any) => s.bangumi.id === bangumiId.value)
    if (sub) {
      isSubscribed.value = true
      subscriptionId.value = sub.id
    }
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function fetchDownloaders() {
  try {
    const response = await downloaderApi.getAll()
    downloaders.value = response.data
  } catch {
    // Error handled by interceptor
  }
}

async function handleSubscribe() {
  try {
    await subscriptionApi.create({
      bangumi_id: bangumiId.value,
      auto_download: subscribeForm.value.auto_download,
      downloader_id: subscribeForm.value.downloader_id ?? undefined,
      save_path: subscribeForm.value.save_path || undefined,
    })
    ElMessage.success('订阅成功')
    showSubscribeDialog.value = false
    isSubscribed.value = true
    await fetchBangumi()
  } catch {
    // Error handled by interceptor
  }
}

async function handleUnsubscribe() {
  if (!subscriptionId.value) return
  try {
    await subscriptionApi.delete(subscriptionId.value)
    ElMessage.success('取消订阅成功')
    isSubscribed.value = false
    subscriptionId.value = null
  } catch {
    // Error handled by interceptor
  }
}

async function handleRefreshEpisodes() {
  refreshing.value = true
  try {
    const response = await bangumiApi.refreshEpisodes(bangumiId.value)
    ElMessage.success(response.data.message || '刷新成功')
    await fetchBangumi()
  } catch {
    // Error handled by interceptor
  } finally {
    refreshing.value = false
  }
}

function copyToClipboard(text: string, label: string = '链接') {
  navigator.clipboard.writeText(text)
  ElMessage.success(`${label}已复制到剪贴板`)
}

async function handleDownload(episode: Episode, type: 'magnet' | 'torrent') {
  const link = type === 'magnet' ? episode.magnet_url : episode.torrent_url
  
  if (!link) {
    ElMessage.warning('该剧集没有对应的下载链接')
    return
  }

  if (downloaders.value.length === 0) {
    copyToClipboard(link, type === 'magnet' ? '磁力链接' : '种子链接')
    return
  }

  const defaultDownloader = downloaders.value.find(d => d.is_default) || downloaders.value[0]

  try {
    const response = await downloaderApi.download({
      episode_ids: [episode.id],
      downloader_id: defaultDownloader.id,
      download_type: type,
    })

    if (response.data.download_url) {
      copyToClipboard(response.data.download_url, '下载链接')
    } else {
      ElMessage.success(response.data.message || '下载任务已添加')
    }
  } catch {
    // Error handled by interceptor
  }
}

onMounted(() => {
  fetchBangumi()
  fetchDownloaders()
})
</script>

<style scoped lang="scss">
.meta {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.description {
  margin-top: 16px;
  color: #606266;
  line-height: 1.6;
}

.actions {
  margin-top: 20px;
}

.episode-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
</style>
