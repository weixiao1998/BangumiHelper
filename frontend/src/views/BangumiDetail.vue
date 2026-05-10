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
            <el-tag v-if="subscriptionFilter" type="warning">已过滤</el-tag>
          </p>
          <p v-if="bangumi.description" class="description">{{ bangumi.description }}</p>

          <div class="actions">
            <el-button v-if="!isSubscribed" type="primary" @click="showSubscribeDialog = true">订阅</el-button>
            <el-button v-else type="danger" @click="handleUnsubscribe">取消订阅</el-button>
            <el-button v-if="isSubscribed" @click="showFilterDialog = true">过滤器</el-button>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <div class="episode-section-header">
        <h3 style="margin: 0;">剧集列表</h3>
        <el-button type="primary" :loading="refreshing" @click="handleRefreshEpisodes">
          刷新剧集
        </el-button>
      </div>
      <div class="subtitle-group-layout">
        <div class="subtitle-sidebar">
          <div
            v-for="group in subtitleGroups"
            :key="group.name"
            class="subtitle-group-item"
            :class="{ active: activeSubtitleGroup === group.name }"
            @mouseenter="activeSubtitleGroup = group.name"
          >
            <div class="group-name">{{ group.name }}</div>
            <div class="group-meta">
              <span class="episode-count">{{ group.episodes.length }} 集</span>
              <span class="latest-time">{{ formatTime(group.latestPublishTime) }}</span>
            </div>
          </div>
          <div v-if="subtitleGroups.length === 0" class="sidebar-empty">
            暂无剧集
          </div>
        </div>
        <div class="episode-list-panel">
          <template v-if="filteredEpisodes.length > 0">
            <div
              v-for="ep in filteredEpisodes"
              :key="ep.id"
              class="episode-card"
              :class="{ 'filtered-out': subscriptionFilter && !matchEpisode(ep) }"
            >
              <div class="episode-card-body">
                <span class="episode-badge">第 {{ ep.episode_number }} 集</span>
                <el-tooltip :disabled="!overflowStates[ep.id]" :content="ep.title" placement="top">
                  <span
                    :ref="el => registerTitleRef(el, ep.id)"
                    class="episode-title"
                  >
                    {{ ep.title }}
                  </span>
                </el-tooltip>
                <span class="episode-time">{{ formatTime(ep.publish_time) }}</span>
              </div>
              <div class="episode-card-actions">
                <el-button
                  v-if="ep.magnet_url"
                  size="small"
                  type="primary"
                  @click="handleDownload(ep, 'magnet')"
                >
                  磁力
                </el-button>
                <el-button
                  v-if="ep.torrent_url"
                  size="small"
                  type="success"
                  @click="handleDownload(ep, 'torrent')"
                >
                  种子
                </el-button>
                <el-button
                  v-if="!ep.magnet_url && !ep.torrent_url"
                  size="small"
                  disabled
                >
                  无下载
                </el-button>
              </div>
            </div>
          </template>
          <div v-else class="episode-list-empty">
            该字幕组暂无剧集
          </div>
        </div>
      </div>
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

    <FilterDialog
      v-model="showFilterDialog"
      :subscription-id="subscriptionId || 0"
      :filter-data="subscriptionFilter"
      :subtitle-group-options="subtitleGroupOptions"
      @saved="handleFilterSaved"
      @deleted="handleFilterDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { bangumiApi, subscriptionApi, downloaderApi } from '@/api'
import FilterDialog from '@/components/FilterDialog.vue'

dayjs.extend(utc)

interface BangumiFilter {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

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
  subtitle_groups?: string | null
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
const subscriptionFilter = ref<BangumiFilter | null>(null)
const downloaders = ref<Downloader[]>([])
const showFilterDialog = ref(false)

const showSubscribeDialog = ref(false)
const subscribeForm = ref({
  auto_download: false,
  downloader_id: null as number | null,
  save_path: '',
})

const overflowStates = ref<Record<number, boolean>>({})
const titleElements = ref<Map<number, HTMLElement>>(new Map())

function registerTitleRef(el: any, episodeId: number) {
  if (el && el instanceof HTMLElement) {
    titleElements.value.set(episodeId, el)
  }
}

function checkAllOverflow() {
  const states: Record<number, boolean> = {}
  titleElements.value.forEach((el, id) => {
    states[id] = el.scrollWidth > el.clientWidth
  })
  overflowStates.value = states
}

function formatTime(time: string | null | undefined): string {
  if (!time) return '-'
  return dayjs.utc(time).local().format('YYYY-MM-DD HH:mm')
}

interface SubtitleGroup {
  name: string
  episodes: Episode[]
  latestPublishTime: string
}

const subtitleGroups = computed<SubtitleGroup[]>(() => {
  const map = new Map<string, Episode[]>()
  for (const ep of episodes.value) {
    const group = ep.subtitle_group || '未知字幕组'
    if (!map.has(group)) map.set(group, [])
    map.get(group)!.push(ep)
  }
  const groups: SubtitleGroup[] = []
  map.forEach((eps, name) => {
    const sorted = [...eps].sort((a, b) => b.episode_number - a.episode_number)
    groups.push({
      name,
      episodes: sorted,
      latestPublishTime: sorted[0]?.publish_time || '',
    })
  })
  return groups.sort((a, b) => b.latestPublishTime.localeCompare(a.latestPublishTime))
})

const activeSubtitleGroup = ref('')

watch(subtitleGroups, (groups) => {
  if (groups.length > 0 && !activeSubtitleGroup.value) {
    activeSubtitleGroup.value = groups[0].name
  }
}, { immediate: true })

const filteredEpisodes = computed(() => {
  const group = subtitleGroups.value.find(g => g.name === activeSubtitleGroup.value)
  return group?.episodes || []
})

const bangumiId = computed(() => Number(route.params.id))

const subtitleGroupOptions = computed(() => {
  if (!bangumi.value?.subtitle_groups) return []
  return bangumi.value.subtitle_groups
    .split(',')
    .map(s => {
      const parts = s.split(':')
      return parts.length > 1 ? parts.slice(1).join(':').trim() : s.trim()
    })
    .filter(Boolean)
})

function matchEpisode(episode: Episode): boolean {
  const f = subscriptionFilter.value
  if (!f) return true

  if (f.include_keywords) {
    const keywords = f.include_keywords.split(',').map(s => s.trim()).filter(Boolean)
    for (const kw of keywords) {
      if (kw.toLowerCase() && !episode.title.toLowerCase().includes(kw.toLowerCase())) {
        return false
      }
    }
  }

  if (f.exclude_keywords) {
    const keywords = f.exclude_keywords.split(',').map(s => s.trim()).filter(Boolean)
    for (const kw of keywords) {
      if (kw.toLowerCase() && episode.title.toLowerCase().includes(kw.toLowerCase())) {
        return false
      }
    }
  }

  if (f.subtitle_groups) {
    const allowed = f.subtitle_groups.split(',').map(s => s.trim()).filter(Boolean)
    if (episode.subtitle_group) {
      if (!allowed.some(a => a.toLowerCase() && episode.subtitle_group.toLowerCase().includes(a.toLowerCase()))) {
        return false
      }
    } else {
      if (allowed.length > 0) return false
    }
  }

  if (f.regex_pattern) {
    try {
      if (!new RegExp(f.regex_pattern).test(episode.title)) return false
    } catch {
      // invalid regex, skip
    }
  }

  if (f.min_episode !== null && f.min_episode !== undefined && episode.episode_number < f.min_episode) return false
  if (f.max_episode !== null && f.max_episode !== undefined && episode.episode_number > f.max_episode) return false

  return true
}

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
      subscriptionFilter.value = sub.filter || null
    }
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
    await nextTick()
    checkAllOverflow()
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
    subscriptionFilter.value = null
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

async function handleFilterSaved() {
  await fetchBangumi()
}

async function handleFilterDeleted() {
  subscriptionFilter.value = null
  await fetchBangumi()
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

.episode-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.subtitle-group-layout {
  display: flex;
  gap: 16px;
  margin-top: 16px;
  min-height: 300px;
}

.subtitle-sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  padding-right: 12px;
  overflow-y: auto;
  max-height: 600px;
}

.subtitle-group-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-bottom: 4px;

  &:hover {
    background-color: #f5f7fa;
  }

  &.active {
    background-color: #ecf5ff;
    color: #409eff;
  }

  .group-name {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .group-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #909399;

    .episode-count {
      flex-shrink: 0;
    }

    .latest-time {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.sidebar-empty {
  padding: 24px 12px;
  text-align: center;
  color: #c0c4cc;
  font-size: 14px;
}

.episode-list-panel {
  flex: 1;
  overflow-y: auto;
  max-height: 600px;
  padding-left: 4px;
}

.episode-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f5f7fa;
  }

  &.filtered-out {
    opacity: 0.5;

    .episode-title {
      text-decoration: line-through;
      color: #c0c4cc;
    }
  }

  .episode-card-body {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
  }

  .episode-badge {
    font-size: 12px;
    font-weight: 600;
    color: #409eff;
    background: #ecf5ff;
    padding: 2px 8px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .episode-title {
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }

  .episode-time {
    font-size: 12px;
    color: #909399;
    flex-shrink: 0;
    white-space: nowrap;
  }

  .episode-card-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
    margin-left: 12px;
  }
}

.episode-list-empty {
  padding: 48px 16px;
  text-align: center;
  color: #c0c4cc;
  font-size: 14px;
}
</style>
