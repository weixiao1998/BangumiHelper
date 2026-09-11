<template>
  <div class="page-container">
    <el-page-header @back="router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">{{ bangumi?.name || '番剧详情' }}</span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="10" animated style="margin-top: 20px" />

    <template v-else-if="bangumi">
      <div class="detail-layout">
        <el-image :src="bangumi.cover || '/placeholder.png'" fit="cover" class="cover-image">
          <template #error>
            <img :src="'/placeholder.png'" alt="" class="cover-image" />
          </template>
        </el-image>
        <div class="detail-content">
          <div class="detail-header">
            <div class="detail-header-left">
              <h2>{{ bangumi.name }}</h2>
              <p class="meta">
                <el-tag>更新: {{ bangumi.update_time }}</el-tag>
                <el-tag type="info">{{ bangumi.data_source }}</el-tag>
                <el-tag v-if="bangumi.seasons && bangumi.seasons.length" type="info">{{ formatSeasons(bangumi.seasons) }}</el-tag>
                <el-tag v-if="activeSource !== 'none'" type="warning">
                  {{ activeSource === 'global' ? '全局过滤' : '自定义过滤' }}
                </el-tag>
              </p>
            </div>
            <div class="detail-header-actions">
              <template v-if="!isSubscribed">
                <el-button type="primary" @click="showSettingsDialog = true">订阅</el-button>
              </template>
              <template v-else>
                <el-button type="danger" @click="handleUnsubscribe">取消订阅</el-button>
                <el-button @click="showSettingsDialog = true">订阅设置</el-button>
              </template>
              <el-button plain :loading="refreshing" @click="handleRefreshEpisodes">
                刷新剧集
              </el-button>
            </div>
          </div>
          <p v-if="bangumi.description" class="description">{{ bangumi.description }}</p>

          <div class="subtitle-group-layout">
            <div class="subtitle-sidebar">
              <div
                v-for="group in subtitleGroups"
                :key="group.name"
                class="subtitle-group-item"
                :class="{ active: activeSubtitleGroup === group.name }"
                @mouseenter="activeSubtitleGroup = group.name"
              >
                <div class="group-name">
                  <span class="group-name-text">{{ group.name }}</span>
                  <el-tag v-if="isGroupSubscribed(group.name)" size="small" type="success" class="group-subscribed-tag">已订阅</el-tag>
                </div>
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
                  :class="{ 'filtered-out': activeSource !== 'none' && !matchedEpisodeIds.has(ep.id) }"
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
                      @click="copyMagnet(ep)"
                    >
                      复制磁力
                    </el-button>
                    <el-button
                      v-if="ep.torrent_url"
                      size="small"
                      type="success"
                      @click="openTorrent(ep)"
                    >
                      下载种子
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
        </div>
      </div>
    </template>

    <!-- 新建订阅与编辑订阅设置共用同一个弹窗（subscriptionId 为空即新建） -->
    <SubscriptionSettingsDialog
      v-model="showSettingsDialog"
      :bangumi-id="bangumiId"
      :bangumi-name="bangumi?.name"
      :subscription-id="subscriptionId"
      :status="subscriptionStatus"
      :filter-data="subscriptionFilter"
      :filter-mode="isSubscribed ? subscriptionMode : undefined"
      :has-global-filter="globalFilterAvailable"
      :subtitle-group-options="subtitleGroupOptions"
      @saved="handleSettingsSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { bangumiApi, subscriptionApi } from '@/api'
import SubscriptionSettingsDialog from '@/components/SubscriptionSettingsDialog.vue'

dayjs.extend(utc)

interface BangumiFilter {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  language: string | null
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
  seasons: string[]
  episodes: Episode[]
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
const subscriptionMode = ref<'inherit' | 'custom'>('inherit')
const subscriptionStatus = ref(1)
const activeSource = ref<'global' | 'custom' | 'none'>('none')
const globalFilterAvailable = ref(false)
const activeSubtitleGroups = ref('')
const matchedEpisodeIds = ref<Set<number>>(new Set())
const showSettingsDialog = ref(false)

const overflowStates = ref<Record<number, boolean>>({})
const titleElements = ref<Map<number, HTMLElement>>(new Map())

function registerTitleRef(el: unknown, episodeId: number) {
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

// 把多个季度合并成一个紧凑标签（如 "2026 春·夏"），供详情页与卡片复用。
const seasonOrder = ['春', '夏', '秋', '冬']
function formatSeasons(seasons: string[]): string {
  const byYear: Record<number, string[]> = {}
  for (const s of seasons) {
    const m = s.match(/^(\d{4})\s+(春|夏|秋|冬)$/)
    if (!m) continue
    const y = Number(m[1])
    const q = m[2]
    ;(byYear[y] ||= []).push(q)
  }
  return Object.keys(byYear)
    .sort((a, b) => Number(a) - Number(b))
    .map((y) => {
      const qs = byYear[Number(y)].sort((a, b) => seasonOrder.indexOf(a) - seasonOrder.indexOf(b))
      return `${y} ${qs.join('·')}`
    })
    .join(' / ')
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

function isGroupSubscribed(groupName: string): boolean {
  // 生效规则的字幕组由后端给出（可能是全局规则，也可能是订阅自己的规则）
  if (!activeSubtitleGroups.value) return false
  const allowed = activeSubtitleGroups.value.split(',').map(s => s.trim()).filter(Boolean)
  return allowed.some(a => a.toLowerCase() && groupName.toLowerCase().includes(a.toLowerCase()))
}

async function fetchBangumi() {
  loading.value = true
  try {
    const response = await bangumiApi.getBangumi(bangumiId.value)
    bangumi.value = response.data
    episodes.value = response.data.episodes || []

    const subResponse = await subscriptionApi.getAll()
    const sub = subResponse.data.find(
      (s: { id: number; bangumi: { id: number }; filter?: BangumiFilter | null }) => s.bangumi.id === bangumiId.value
    )
    if (sub) {
      isSubscribed.value = true
      subscriptionId.value = sub.id
      subscriptionFilter.value = sub.filter || null
      subscriptionMode.value = sub.filter_mode || 'inherit'
      subscriptionStatus.value = sub.status ?? 1
    } else {
      isSubscribed.value = false
      subscriptionId.value = null
      subscriptionFilter.value = null
      subscriptionMode.value = 'inherit'
    }
    await fetchFiltering()
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
    await nextTick()
    checkAllOverflow()
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
    subscriptionMode.value = 'inherit'
    subscriptionStatus.value = 1
    activeSource.value = 'none'
    activeSubtitleGroups.value = ''
    matchedEpisodeIds.value = new Set()
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

// 下载一律在本地完成：复制磁力交给本机客户端，或下载 .torrent 文件。
// 服务器不代管下载器（公网实例够不到用户家里的下载器），详见 documents/auto-download-redesign.md
function copyMagnet(episode: Episode) {
  if (!episode.magnet_url) {
    ElMessage.warning('该剧集没有磁力链接')
    return
  }
  copyToClipboard(episode.magnet_url, '磁力链接')
}

function openTorrent(episode: Episode) {
  if (!episode.torrent_url) {
    ElMessage.warning('该剧集没有种子链接')
    return
  }
  window.open(episode.torrent_url, '_blank', 'noopener')
}

async function fetchFiltering() {
  if (!subscriptionId.value) {
    activeSource.value = 'none'
    activeSubtitleGroups.value = ''
    matchedEpisodeIds.value = new Set()
    return
  }
  try {
    const { data } = await subscriptionApi.filtering(subscriptionId.value)
    activeSource.value = data.active_source
    globalFilterAvailable.value = data.global_filter_available
    activeSubtitleGroups.value = data.active_subtitle_groups || ''
    matchedEpisodeIds.value = new Set<number>(data.matched_episode_ids || [])
  } catch {
    // Error handled by interceptor
  }
}

async function handleSettingsSaved() {
  await fetchBangumi()
}

onMounted(() => {
  fetchBangumi()
})
</script>

<style scoped lang="scss">
.detail-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  margin-top: 20px;

  @media (max-width: 768px) {
    flex-direction: column;

    .cover-image {
      width: 100%;
    }
  }
}

.cover-image {
  width: 300px;
  flex-shrink: 0;
  border-radius: 8px;
}

.detail-content {
  flex: 1;
  min-width: 0;

  h2 {
    line-height: 1.4;
  }
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.description {
  margin-top: 16px;
  color: #606266;
  line-height: 1.6;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.detail-header-left {
  flex: 1;
  min-width: 0;
}

.detail-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
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
  max-height: calc(100vh - 280px);
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
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;

    .group-name-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .group-subscribed-tag {
      flex-shrink: 0;
    }
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
  max-height: calc(100vh - 280px);
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
