<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>我的订阅</h2>
        <p class="page-subtitle">共 {{ groups.length }} 组 · {{ subscriptions.length }} 条订阅</p>
      </div>
      <el-button type="primary" @click="openCreateGroup">新建订阅组</el-button>
    </div>

    <el-skeleton v-if="loading" :rows="10" animated />

    <el-empty v-else-if="groups.length === 0" description="还没有订阅组">
      <el-button type="primary" @click="openCreateGroup">新建订阅组</el-button>
    </el-empty>

    <div v-else class="subscriptions-layout">
      <aside class="group-sidebar">
        <button
          v-for="group in groups"
          :key="group.id"
          type="button"
          class="group-item"
          :class="{ active: group.id === selectedGroupId, paused: group.status === 0 }"
          @click="selectGroup(group.id)"
        >
          <span class="group-item-name" :title="group.name">{{ group.name }}</span>
          <span class="group-item-meta">
            <span>{{ subscriptionsByGroup.get(group.id)?.length || 0 }} 条</span>
            <span v-if="group.status === 0" class="paused-text">暂停</span>
          </span>
        </button>
      </aside>

      <section v-if="selectedGroup" class="group-content">
        <div class="group-header">
          <div class="group-title-wrap">
            <div class="group-title-line">
              <h3>{{ selectedGroup.name }}</h3>
              <el-tag v-if="selectedGroup.status === 0" type="info" size="small">已暂停</el-tag>
            </div>
            <p v-if="selectedGroup.description" class="group-description">{{ selectedGroup.description }}</p>
          </div>
          <div class="group-actions">
            <el-switch
              :model-value="selectedGroup.status === 1"
              active-text="启用"
              inactive-text="暂停"
              @change="toggleGroupStatus"
            />
            <el-button size="small" @click="openEditGroup(selectedGroup)">组设置</el-button>
            <el-button size="small" @click="showGroupRss(selectedGroup)">组 RSS</el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="groups.length <= 1"
              :title="groups.length <= 1 ? '至少保留一个订阅组' : '删除订阅组'"
              @click="handleDeleteGroup(selectedGroup)"
            >
              删除
            </el-button>
          </div>
        </div>

        <el-alert
          v-if="selectedGroup.status === 0"
          type="warning"
          :closable="false"
          show-icon
          title="该订阅组已暂停"
          description="组 RSS 返回 404；用户级「全部订阅」RSS 也会跳过本组。组内订阅配置与规则会保留。"
          class="paused-alert"
        />

        <el-empty v-if="groupSubscriptions.length === 0" class="group-empty" description="该组暂无订阅">
          <el-button type="primary" @click="router.push('/')">去番剧日历订阅</el-button>
        </el-empty>

        <el-row v-else class="subscription-grid" :gutter="12">
          <el-col v-for="sub in groupSubscriptions" :key="sub.id" :xs="12" :sm="8" :md="6" :lg="4" :xl="3">
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
                <span v-if="pausedBadge(sub)" class="status-badge status-badge--paused" :title="pausedBadgeTitle(sub)">
                  {{ pausedBadge(sub) }}
                </span>
              </div>
              <div class="info">
                <h4 class="name" :title="sub.bangumi.name">{{ sub.bangumi.name }}</h4>
                <div class="actions" @click.stop>
                  <button type="button" class="action" title="订阅设置：所属组、过滤规则与暂停" @click="openSettings(sub)">
                    设置
                  </button>
                  <button type="button" class="action action--danger" title="取消订阅" @click="handleUnsubscribe(sub)">
                    取消
                  </button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </section>
    </div>

    <el-dialog v-model="rssDialogVisible" :title="`组 RSS · ${rssGroup?.name || ''}`" width="520px">
      <p>将以下链接添加到 RSS 阅读器或下载工具中：</p>
      <el-input v-model="rssUrl" type="textarea" :rows="3" readonly style="margin-bottom: 12px" />
      <el-alert
        v-if="rssGroup?.status === 0"
        type="warning"
        :closable="false"
        show-icon
        title="该组当前已暂停"
        description="暂停期间该 feed 返回 404；启用组后链接会自动恢复。"
        style="margin-bottom: 12px"
      />
      <p class="hint">
        该 feed 只包含本组启用的订阅，过滤规则已由服务端应用。暂停本组或组内订阅后，内容不再输出。
        如果链接泄露，可以重新生成。
      </p>
      <template #footer>
        <el-button @click="rssDialogVisible = false">关闭</el-button>
        <el-button @click="handleRegenerateToken">重新生成</el-button>
        <el-button type="primary" @click="copyRssUrl">复制链接</el-button>
      </template>
    </el-dialog>

    <SubscriptionGroupDialog
      v-model="groupDialogVisible"
      :group="editingGroup"
      @saved="handleGroupSaved"
    />

    <SubscriptionSettingsDialog
      v-model="settingsVisible"
      :bangumi-id="settingsTarget?.bangumi.id || 0"
      :bangumi-name="settingsTarget?.bangumi.name"
      :subscription-id="settingsTarget?.id"
      :group-id="settingsTarget?.group_id"
      :groups="groups"
      :occupied-group-ids="settingsTarget ? occupiedGroupIdsFor(settingsTarget) : []"
      :status="settingsTarget?.status"
      :filter-data="settingsTarget?.filter || null"
      :filter-mode="settingsTarget?.filter_mode"
      :subtitle-group-options="parseSubtitleGroups(settingsTarget?.bangumi.subtitle_groups)"
      @saved="handleSubscriptionSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { groupApi, rssApi, subscriptionApi } from '@/api'
import SubscriptionGroupDialog from '@/components/SubscriptionGroupDialog.vue'
import SubscriptionSettingsDialog from '@/components/SubscriptionSettingsDialog.vue'
import type { Subscription, SubscriptionGroup } from '@/types'
import { parseSubtitleGroups, ruleHasConditions } from '@/utils/filter'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const groups = ref<SubscriptionGroup[]>([])
const subscriptions = ref<Subscription[]>([])
const selectedGroupId = ref<number | null>(null)

const groupDialogVisible = ref(false)
const editingGroup = ref<SubscriptionGroup | null>(null)

const settingsVisible = ref(false)
const settingsTarget = ref<Subscription | null>(null)

const rssDialogVisible = ref(false)
const rssGroup = ref<SubscriptionGroup | null>(null)
const rssUrl = ref('')

const selectedGroup = computed(
  () => groups.value.find(group => group.id === selectedGroupId.value) || null,
)

const subscriptionsByGroup = computed(() => {
  const map = new Map<number, Subscription[]>()
  for (const sub of subscriptions.value) {
    if (!map.has(sub.group_id)) map.set(sub.group_id, [])
    map.get(sub.group_id)!.push(sub)
  }
  return map
})

const groupSubscriptions = computed(() =>
  selectedGroup.value ? subscriptionsByGroup.value.get(selectedGroup.value.id) || [] : [],
)

function selectGroup(groupId: number) {
  selectedGroupId.value = groupId
  router.replace({ query: { ...route.query, group: String(groupId) } })
}

async function fetchData() {
  loading.value = true
  try {
    const [groupsResponse, subscriptionsResponse] = await Promise.all([
      groupApi.getAll(),
      subscriptionApi.getAll(),
    ])
    groups.value = groupsResponse.data
    subscriptions.value = subscriptionsResponse.data

    const queryGroupId = Number(route.query.group)
    const queryValid = groups.value.some(group => group.id === queryGroupId)
    const currentValid = groups.value.some(group => group.id === selectedGroupId.value)
    if (queryValid) {
      selectedGroupId.value = queryGroupId
    } else if (!currentValid) {
      selectedGroupId.value = groups.value[0]?.id ?? null
    }
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query.group,
  (value) => {
    const groupId = Number(value)
    if (groupId && groups.value.some(group => group.id === groupId)) {
      selectedGroupId.value = groupId
    }
  },
)

function openCreateGroup() {
  editingGroup.value = null
  groupDialogVisible.value = true
}

function openEditGroup(group: SubscriptionGroup) {
  editingGroup.value = group
  groupDialogVisible.value = true
}

async function handleGroupSaved(group?: SubscriptionGroup) {
  await fetchData()
  if (group?.id && groups.value.some(item => item.id === group.id)) {
    selectGroup(group.id)
  }
}

async function toggleGroupStatus() {
  const group = selectedGroup.value
  if (!group) return
  try {
    await groupApi.update(group.id, { status: group.status === 1 ? 0 : 1 })
    ElMessage.success(group.status === 1 ? '订阅组已暂停' : '订阅组已启用')
    await fetchData()
  } catch {
    // Error handled by interceptor
  }
}

async function handleDeleteGroup(group: SubscriptionGroup) {
  if (groups.value.length <= 1) {
    ElMessage.warning('至少保留一个订阅组')
    return
  }
  const count = subscriptionsByGroup.value.get(group.id)?.length || 0
  const message = count
    ? `订阅组「${group.name}」还有 ${count} 个订阅，删除后将一并取消这些订阅，且不可恢复。`
    : `确定删除订阅组「${group.name}」？`
  try {
    await ElMessageBox.confirm(message, '删除订阅组', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await groupApi.delete(group.id, count > 0)
    ElMessage.success(count ? `订阅组已删除，同时取消 ${count} 个订阅` : '订阅组已删除')
    if (selectedGroupId.value === group.id) selectedGroupId.value = null
    await fetchData()
  } catch {
    // Error handled by interceptor
  }
}

function openSettings(sub: Subscription) {
  settingsTarget.value = sub
  settingsVisible.value = true
}

function occupiedGroupIdsFor(sub: Subscription): number[] {
  return subscriptions.value
    .filter(item => item.bangumi.id === sub.bangumi.id)
    .map(item => item.group_id)
}

async function handleSubscriptionSaved() {
  await fetchData()
}

async function handleUnsubscribe(sub: Subscription) {
  try {
    await ElMessageBox.confirm(`确定取消订阅「${sub.bangumi.name}」？`, '取消订阅', {
      type: 'warning',
      confirmButtonText: '取消订阅',
      cancelButtonText: '保留',
    })
  } catch {
    return
  }

  try {
    await subscriptionApi.delete(sub.id)
    ElMessage.success('取消订阅成功')
    await fetchData()
  } catch {
    // Error handled by interceptor
  }
}

function filterBadge(sub: Subscription): string {
  if (sub.filter_mode === 'custom') {
    return ruleHasConditions(sub.filter) ? '自定义过滤' : ''
  }
  const group = groups.value.find(item => item.id === sub.group_id)
  return ruleHasConditions(group) ? '组规则' : ''
}

function filterBadgeTitle(sub: Subscription): string {
  return sub.filter_mode === 'custom'
    ? '使用该订阅自己的过滤规则（组规则不生效）'
    : '继承该订阅组的默认规则'
}

function pausedBadge(sub: Subscription): string {
  if (sub.status === 0) return '已暂停'
  if (sub.group.status === 0) return '组已暂停'
  return ''
}

function pausedBadgeTitle(sub: Subscription): string {
  if (sub.status === 0) return '该订阅已暂停'
  return '所属订阅组已暂停，RSS 不会输出该订阅'
}

async function showGroupRss(group: SubscriptionGroup) {
  rssGroup.value = group
  let token = group.rss_token
  if (!token) {
    try {
      const response = await rssApi.regenerateGroupToken(group.id)
      token = response.data.rss_token
      group.rss_token = token
    } catch {
      return
    }
  }
  if (!token) return
  rssUrl.value = buildGroupRssUrl(group.id, token)
  rssDialogVisible.value = true
}

function buildGroupRssUrl(groupId: number, token: string): string {
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
  return `${baseUrl}${rssApi.groupFeedUrl(groupId)}?token=${token}`
}

async function handleRegenerateToken() {
  if (!rssGroup.value) return
  try {
    const response = await rssApi.regenerateGroupToken(rssGroup.value.id)
    const token = response.data.rss_token
    rssGroup.value.rss_token = token
    rssUrl.value = buildGroupRssUrl(rssGroup.value.id, token)
    ElMessage.success('已重新生成组 RSS 链接')
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

onMounted(fetchData)
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }

  .page-subtitle {
    margin: 4px 0 0;
    color: #909399;
    font-size: 13px;
  }
}

.subscriptions-layout {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.group-sidebar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 220px;
  flex-shrink: 0;
}

.group-item {
  width: 100%;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }

  &.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
  }

  &.paused {
    .group-item-name {
      color: #909399;
    }
  }

  .group-item-name {
    display: block;
    overflow: hidden;
    color: #303133;
    font-size: 14px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .group-item-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 6px;
    color: #909399;
    font-size: 12px;
  }

  .paused-text {
    color: var(--el-color-warning);
  }
}

.group-content {
  flex: 1;
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.group-title-line {
  display: flex;
  align-items: center;
  gap: 8px;

  h3 {
    margin: 0;
  }
}

.group-description {
  max-width: 620px;
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
  line-height: 1.5;
}

.group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.subscription-grid,
.group-empty {
  margin-top: 16px;
}

.paused-alert {
  margin: 16px 0;
}

.hint {
  margin: 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
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

@media (max-width: 768px) {
  .subscriptions-layout {
    flex-direction: column;
  }

  .group-sidebar {
    flex-direction: row;
    width: 100%;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .group-item {
    min-width: 150px;
  }

  .group-header {
    flex-direction: column;
  }
}
</style>
