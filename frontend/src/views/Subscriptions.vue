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
      <el-row :gutter="12">
        <el-col v-for="sub in subscriptions" :key="sub.id" :xs="12" :sm="8" :md="6" :lg="4" :xl="3">
          <el-card class="subscription-card" shadow="hover" @click="router.push(`/bangumi/${sub.bangumi.id}`)">
            <div class="cover-wrap">
              <el-image :src="sub.bangumi.cover || '/placeholder.png'" fit="cover" class="cover">
                <template #error>
                  <img :src="'/placeholder.png'" alt="" class="cover" />
                </template>
              </el-image>
              <span v-if="filterBadge(sub)" class="status-badge" :title="filterBadgeTitle(sub)">
                {{ filterBadge(sub) }}
              </span>
              <span v-if="sub.status === 0" class="status-badge status-badge--paused" title="订阅已暂停">已暂停</span>
            </div>
            <div class="info">
              <h4 class="name" :title="sub.bangumi.name">{{ sub.bangumi.name }}</h4>
              <div class="actions" @click.stop>
                <button type="button" class="action" title="订阅设置：过滤规则与暂停" @click="openSettings(sub)">设置</button>
                <button type="button" class="action" title="查看 RSS 订阅链接" @click="showRssDialog(sub)">RSS</button>
                <button
                  type="button"
                  class="action action--danger"
                  title="取消订阅"
                  @click="handleUnsubscribe(sub.id)"
                >
                  取消
                </button>
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
      <p style="color: #909399; font-size: 12px;">暂停订阅、过滤规则请在卡片上的「设置」里调整。</p>
      <template #footer>
        <el-button @click="rssDialogVisible = false">关闭</el-button>
        <el-button @click="handleRegenerateToken">重新生成</el-button>
        <el-button type="primary" @click="copyRssUrl">复制链接</el-button>
      </template>
    </el-dialog>

    <SubscriptionSettingsDialog
      v-model="settingsVisible"
      :bangumi-id="settingsTarget?.bangumi.id || 0"
      :bangumi-name="settingsTarget?.bangumi.name"
      :subscription-id="settingsTarget?.id"
      :status="settingsTarget?.status"
      :filter-data="settingsTarget?.filter || null"
      :filter-mode="settingsTarget?.filter_mode"
      :has-global-filter="hasGlobalFilter"
      :subtitle-group-options="parseSubtitleGroups(settingsTarget?.bangumi.subtitle_groups)"
      @saved="handleFilterSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { subscriptionApi, rssApi, userApi } from '@/api'
import SubscriptionSettingsDialog from '@/components/SubscriptionSettingsDialog.vue'

interface BangumiFilter {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  language: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

interface Subscription {
  id: number
  status: number
  filter_mode: string
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
const rssUrl = ref('')
const currentRssSubscription = ref<Subscription | null>(null)
const settingsVisible = ref(false)
const settingsTarget = ref<Subscription | null>(null)
// 用户的全局默认规则对象：只有"真的有条件"时继承模式才值得标注
const globalFilter = ref<BangumiFilter | null>(null)
const hasGlobalFilter = computed(() => ruleHasConditions(globalFilter.value))

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
      const response = await rssApi.regenerateSubscriptionToken(sub.id)
      token = response.data.rss_token
      sub.rss_token = token
    } catch {
      return
    }
  }
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
  rssUrl.value = `${baseUrl}${rssApi.subscriptionFeedUrl(sub.id)}?token=${token}`
  rssDialogVisible.value = true
}

function openSettings(sub: Subscription) {
  settingsTarget.value = sub
  settingsVisible.value = true
}

// 规则是否真的设置了条件（空规则 == 不过滤，不该显示成"已过滤"）
function ruleHasConditions(rule: BangumiFilter | null | undefined): boolean {
  if (!rule) return false
  return Boolean(
    rule.include_keywords ||
      rule.exclude_keywords ||
      rule.subtitle_groups ||
      rule.language ||
      rule.regex_pattern ||
      (rule.min_episode !== null && rule.min_episode !== undefined) ||
      (rule.max_episode !== null && rule.max_episode !== undefined),
  )
}

// 卡片角标：只标注“真的有规则在生效”的情况
function filterBadge(sub: Subscription): string {
  if (sub.filter_mode === 'custom') return ruleHasConditions(sub.filter) ? '自定义过滤' : ''
  return hasGlobalFilter.value ? '全局过滤' : ''
}

function filterBadgeTitle(sub: Subscription): string {
  return sub.filter_mode === 'custom' ? '使用该订阅自己的过滤规则（全局规则不生效）' : '继承全局默认规则'
}

async function fetchGlobalFilter() {
  try {
    const response = await userApi.getGlobalFilter()
    globalFilter.value = response.data || null
  } catch {
    // Error handled by interceptor
  }
}

async function handleRegenerateToken() {
  if (!currentRssSubscription.value) return
  try {
    const response = await rssApi.regenerateSubscriptionToken(currentRssSubscription.value.id)
    const token = response.data.rss_token
    currentRssSubscription.value.rss_token = token
    const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
    rssUrl.value = `${baseUrl}${rssApi.subscriptionFeedUrl(currentRssSubscription.value.id)}?token=${token}`
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
  await fetchGlobalFilter()
}

onMounted(() => {
  fetchSubscriptions()
  fetchGlobalFilter()
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
  margin-bottom: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;

  :deep(.el-card__body) {
    padding: 10px;
  }

  &:hover {
    transform: translateY(-4px);
  }

  // 封面：圆角裁切 + 悬停轻微放大，避免图片边缘生硬
  .cover-wrap {
    position: relative;
    overflow: hidden;
    border-radius: 8px;
    aspect-ratio: 3 / 4;
    background: #f2f3f5;
  }

  .cover {
    display: block;
    width: 100%;
    height: 100%;
    transition: transform 0.3s ease;
  }

  &:hover .cover {
    transform: scale(1.04);
  }

  // 过滤状态作为封面角标，不再单独占一行
  .status-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    line-height: 16px;
    color: #fff;
    background: rgba(230, 162, 60, 0.92);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);

    &--paused {
      right: 8px;
      left: auto;
      background: rgba(144, 147, 153, 0.92);
    }
  }

  .info {
    padding: 10px 2px 2px;
  }

  // 标题固定两行高度，卡片底部对齐、长标题自动省略
  .name {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    height: 2.6em;
    margin: 0 0 8px;
    color: #303133;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.3;
    word-break: break-word;
  }

  // 三段式操作条：浅灰底等宽分割，替代三个实心按钮的视觉噪音
  .actions {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 2px;
    border-radius: 8px;
    background: #f5f7fa;
  }

  .action {
    flex: 1 1 0;
    min-width: 0;
    height: 28px;
    padding: 0 2px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #606266;
    font-family: inherit;
    font-size: 12px;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;

    &:hover {
      background: #fff;
      color: var(--el-color-primary);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    &:focus-visible {
      outline: 2px solid var(--el-color-primary-light-5);
      outline-offset: 1px;
    }

    &--danger:hover {
      background: var(--el-color-danger-light-9);
      color: var(--el-color-danger);
    }
  }
}
</style>
