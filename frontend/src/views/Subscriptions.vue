<template>
  <div class="page-container">
    <div class="page-header">
      <h2>我的订阅</h2>
    </div>

    <el-skeleton v-if="loading" :rows="10" animated />

    <el-empty v-else-if="subscriptions.length === 0" description="暂无订阅">
      <el-button type="primary" @click="router.push('/')">去订阅</el-button>
    </el-empty>

    <template v-else>
      <el-row :gutter="20">
        <el-col v-for="sub in subscriptions" :key="sub.id" :span="6">
          <el-card class="subscription-card" @click="router.push(`/bangumi/${sub.bangumi.id}`)">
            <el-image :src="sub.bangumi.cover || '/placeholder.png'" fit="cover" class="cover" />
            <div class="info">
              <h4>{{ sub.bangumi.name }}</h4>
              <el-tag v-if="sub.filter" size="small" type="warning" style="margin-bottom: 8px;">已过滤</el-tag>
              <div class="actions" @click.stop>
                <el-button size="small" @click="showFilterDialog(sub)">过滤</el-button>
                <el-button size="small" @click="showRssDialog(sub)">RSS</el-button>
                <el-button size="small" type="danger" @click="handleUnsubscribe(sub.id)">取消</el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-dialog v-model="rssDialogVisible" title="RSS 订阅链接" width="500px">
      <p>将以下链接添加到您的 RSS 阅读器中：</p>
      <el-input
        v-model="rssUrl"
        type="textarea"
        :rows="3"
        readonly
        style="margin-bottom: 16px"
      />
      <p style="color: #909399; font-size: 12px;">如果链接泄露，可以点击"重新生成"按钮获取新链接</p>
      <template #footer>
        <el-button @click="rssDialogVisible = false">关闭</el-button>
        <el-button @click="handleRegenerateToken">重新生成</el-button>
        <el-button type="primary" @click="copyRssUrl">复制链接</el-button>
      </template>
    </el-dialog>

    <FilterDialog
      v-model="filterDialogVisible"
      :subscription-id="filterSubscriptionId"
      :filter-data="filterData"
      :subtitle-group-options="filterSubtitleGroups"
      @saved="handleFilterSaved"
      @deleted="handleFilterDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { subscriptionApi, downloaderApi } from '@/api'
import FilterDialog from '@/components/FilterDialog.vue'

interface BangumiFilter {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

interface Subscription {
  id: number
  rss_token?: string
  bangumi: {
    id: number
    name: string
    cover: string
    subtitle_groups?: string | null
  }
  filter: BangumiFilter | null
}

const router = useRouter()

const loading = ref(true)
const subscriptions = ref<Subscription[]>([])
const rssDialogVisible = ref(false)
const filterDialogVisible = ref(false)
const rssUrl = ref('')
const currentRssSubscription = ref<Subscription | null>(null)
const filterSubscriptionId = ref(0)
const filterData = ref<BangumiFilter | null>(null)
const filterSubtitleGroups = ref<string[]>([])

function parseSubtitleGroups(val: string | null | undefined): string[] {
  if (!val) return []
  return val
    .split(',')
    .map(s => {
      const parts = s.split(':')
      return parts.length > 1 ? parts.slice(1).join(':').trim() : s.trim()
    })
    .filter(Boolean)
}

async function fetchSubscriptions() {
  loading.value = true
  try {
    const response = await subscriptionApi.getAll()
    subscriptions.value = response.data
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function showRssDialog(sub: Subscription) {
  currentRssSubscription.value = sub
  let token = sub.rss_token
  if (!token) {
    try {
      const response = await downloaderApi.regenerateRssToken(sub.id)
      token = response.data.rss_token
      sub.rss_token = token
    } catch {
      return
    }
  }
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
  rssUrl.value = `${baseUrl}/api/downloaders/rss/${sub.id}?token=${token}`
  rssDialogVisible.value = true
}

function showFilterDialog(sub: Subscription) {
  filterSubscriptionId.value = sub.id
  filterData.value = sub.filter || null
  filterSubtitleGroups.value = parseSubtitleGroups(sub.bangumi.subtitle_groups)
  filterDialogVisible.value = true
}

async function handleRegenerateToken() {
  if (!currentRssSubscription.value) return
  try {
    const response = await downloaderApi.regenerateRssToken(currentRssSubscription.value.id)
    const token = response.data.rss_token
    currentRssSubscription.value.rss_token = token
    const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
    rssUrl.value = `${baseUrl}/api/downloaders/rss/${currentRssSubscription.value.id}?token=${token}`
    ElMessage.success('已重新生成RSS链接')
  } catch {
    // Error handled by interceptor
  }
}

async function copyRssUrl() {
  try {
    await navigator.clipboard.writeText(rssUrl.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function handleUnsubscribe(id: number) {
  try {
    await subscriptionApi.delete(id)
    ElMessage.success('取消订阅成功')
    await fetchSubscriptions()
  } catch {
    // Error handled by interceptor
  }
}

async function handleFilterSaved() {
  await fetchSubscriptions()
}

async function handleFilterDeleted() {
  await fetchSubscriptions()
}

onMounted(() => {
  fetchSubscriptions()
})
</script>

<style scoped lang="scss">
.page-header {
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}

.subscription-card {
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-4px);
  }

  .cover {
    width: 100%;
    aspect-ratio: 3/4;
    border-radius: 4px;
  }

  .info {
    padding: 12px 0;

    h4 {
      margin: 0 0 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      margin: 0 0 12px;
      color: #909399;
      font-size: 14px;
    }

    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
  }
}
</style>
