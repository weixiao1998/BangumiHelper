<template>
  <div class="episode-page">
    <div class="episode-card-wrap">
      <el-skeleton v-if="loading" :rows="6" animated />

      <el-result
        v-else-if="error"
        icon="warning"
        title="剧集不存在"
        :sub-title="error"
      >
        <template #extra>
          <el-button type="primary" @click="router.push('/')">返回首页</el-button>
        </template>
      </el-result>

      <template v-else-if="episode">
        <div class="episode-layout">
          <el-image :src="cover" fit="cover" class="cover-image">
            <template #error>
              <img src="/placeholder.png" alt="" class="cover-image" />
            </template>
          </el-image>

          <div class="episode-content">
            <div class="episode-bangumi">
              <span>{{ episode.bangumi_name }}</span>
              <el-button
                text
                type="primary"
                size="small"
                class="bangumi-link"
                @click="openBangumi"
              >
                番剧详情
              </el-button>
            </div>

            <h2 class="episode-title">
              <el-tag effect="dark" class="episode-badge">第 {{ episode.episode_number }} 集</el-tag>
              <span>{{ episode.title }}</span>
            </h2>

            <p class="episode-meta">
              <el-tag v-if="episode.subtitle_group" type="info">{{ episode.subtitle_group }}</el-tag>
              <el-tag v-if="episode.file_size" type="info">{{ formatSize(episode.file_size) }}</el-tag>
              <el-tag v-if="episode.data_source" type="info">{{ episode.data_source }}</el-tag>
              <el-tag type="info">{{ formatTime(episode.publish_time) }}</el-tag>
            </p>

            <div class="episode-actions">
              <el-button v-if="episode.torrent_url" type="success" @click="downloadTorrent">
                下载种子
              </el-button>
              <el-button v-if="episode.magnet_url" type="primary" @click="copyMagnet">
                复制磁力
              </el-button>
              <el-button v-if="episode.torrent_url" @click="copyTorrent">复制种子链接</el-button>
              <el-button v-if="!episode.torrent_url && !episode.magnet_url" disabled>无下载地址</el-button>
            </div>

            <p class="episode-hint">
              下载请在本机完成：复制磁力交给下载器，或下载 .torrent 文件导入。
            </p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { bangumiApi } from '@/api'
import { coverThumb } from '@/utils/cover'

dayjs.extend(utc)

interface EpisodeDetail {
  id: number
  bangumi_id: number
  bangumi_name: string
  bangumi_cover: string | null
  data_source: string
  title: string
  episode_number: number
  torrent_url: string | null
  magnet_url: string | null
  file_size: number | null
  subtitle_group: string | null
  publish_time: string | null
}

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const episode = ref<EpisodeDetail | null>(null)

const cover = computed(() => coverThumb(episode.value?.bangumi_cover, 480))

function formatTime(time: string | null): string {
  if (!time) return '未知时间'
  return dayjs.utc(time).local().format('YYYY-MM-DD HH:mm')
}

function formatSize(size: number): string {
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

async function fetchEpisode() {
  loading.value = true
  error.value = ''
  try {
    const response = await bangumiApi.getEpisode(Number(route.params.id))
    episode.value = response.data as EpisodeDetail
    document.title = `${episode.value.bangumi_name} 第 ${episode.value.episode_number} 集 - BangumiHelper`
  } catch {
    // 拦截器已提示，这里只负责渲染"剧集不存在"而不是空白页
    error.value = '该剧集可能已被清理，请回到订阅列表查看最新内容。'
  } finally {
    loading.value = false
  }
}

function openBangumi() {
  if (!episode.value) return
  router.push(`/bangumi/${episode.value.bangumi_id}`)
}

async function copyText(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${label}已复制到剪贴板`)
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}

function copyMagnet() {
  if (!episode.value?.magnet_url) return
  copyText(episode.value.magnet_url, '磁力链接')
}

function copyTorrent() {
  if (!episode.value?.torrent_url) return
  copyText(episode.value.torrent_url, '种子链接')
}

// 种子文件依赖浏览器的下载行为，这里显式用新标签页打开，避免走页面导航
function downloadTorrent() {
  if (!episode.value?.torrent_url) return
  window.open(episode.value.torrent_url, '_blank', 'noopener')
}

onMounted(fetchEpisode)
</script>

<style scoped lang="scss">
.episode-page {
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: #f5f7fa;
}

.episode-card-wrap {
  width: 100%;
  max-width: 820px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.episode-layout {
  display: flex;
  gap: 24px;

  @media (max-width: 640px) {
    flex-direction: column;

    .cover-image {
      width: 100%;
      max-width: 240px;
      margin: 0 auto;
    }
  }
}

.cover-image {
  width: 200px;
  flex-shrink: 0;
  border-radius: 8px;
  aspect-ratio: 3 / 4;
  background-color: var(--el-fill-color-light);
}

.episode-content {
  flex: 1;
  min-width: 0;
}

.episode-bangumi {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #909399;

  .bangumi-link {
    padding: 0;
  }
}

.episode-title {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 10px;
  font-size: 20px;
  line-height: 1.5;
  word-break: break-word;

  .episode-badge {
    flex-shrink: 0;
    margin-top: 2px;
  }
}

.episode-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.episode-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}

.episode-hint {
  margin-top: 16px;
  font-size: 12px;
  color: #909399;
}
</style>
