<template>
  <div class="page-container">
    <div class="page-header">
      <h2>设置</h2>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="个人信息" name="profile">
        <el-card>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ userStore.user?.username }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ userStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag v-if="userStore.isAdmin" type="danger">管理员</el-tag>
              <el-tag v-else>普通用户</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-card>
          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px" style="max-width: 400px">
            <el-form-item label="原密码" prop="oldPassword">
              <el-input v-model="passwordForm.oldPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="passwordForm.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="全局过滤" name="global-filter">
        <el-card>
          <el-form :model="globalFilterForm" label-width="100px" style="max-width: 500px">
            <el-form-item label="包含关键词">
              <el-select
                v-model="globalFilterForm.include_keywords"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入关键词后回车添加"
                popper-class="hide-select-dropdown"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="排除关键词">
              <el-select
                v-model="globalFilterForm.exclude_keywords"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入关键词后回车添加"
                popper-class="hide-select-dropdown"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="字幕组">
              <el-select
                v-model="globalFilterForm.subtitle_groups"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入字幕组名称后回车添加"
                popper-class="hide-select-dropdown"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="集数范围">
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-input-number v-model="globalFilterForm.min_episode" :min="0" :max="9999" placeholder="最小" controls-position="right" />
                <span>—</span>
                <el-input-number v-model="globalFilterForm.max_episode" :min="0" :max="9999" placeholder="最大" controls-position="right" />
              </div>
            </el-form-item>

            <el-form-item>
              <el-button link type="primary" @click="showAdvanced = !showAdvanced">
                {{ showAdvanced ? '收起高级选项' : '展开高级选项' }}
              </el-button>
            </el-form-item>

            <template v-if="showAdvanced">
              <el-form-item label="正则匹配">
                <el-input v-model="globalFilterForm.regex_pattern" placeholder="正则表达式匹配标题" />
              </el-form-item>
            </template>

            <el-form-item>
              <el-button v-if="hasGlobalFilter" type="primary" :loading="filterLoading" @click="handleUpdateGlobalFilter">更新过滤器</el-button>
              <el-button v-else type="primary" :loading="filterLoading" @click="handleCreateGlobalFilter">创建过滤器</el-button>
              <el-button v-if="hasGlobalFilter" type="danger" :loading="filterLoading" @click="handleDeleteGlobalFilter">删除过滤器</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="hasGlobalFilter"
            title="全局过滤器已启用"
            type="success"
            :closable="false"
            style="margin-top: 16px"
          >
            此过滤器将应用于您的所有订阅。您可以为单个订阅设置额外的过滤器，两者将同时生效。
          </el-alert>
          <el-alert
            v-else
            title="全局过滤器未设置"
            type="info"
            :closable="false"
            style="margin-top: 16px"
          >
            设置全局过滤器后，它将自动应用于您的所有订阅的 RSS 输出和剧集列表。
          </el-alert>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="userStore.isAdmin" label="数据管理" name="data">
        <el-card>
          <el-form label-width="100px">
            <el-form-item label="数据源">
              <el-select v-model="dataSource" style="width: 200px">
                <el-option label="蜜柑计划" value="mikan" />
                <el-option label="bangumi.moe" value="bangumi_moe" />
                <el-option label="动漫花园" value="dmhy" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="refreshLoading" @click="handleRefresh">刷新番剧列表</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="RSS 订阅" name="rss">
        <el-card>
          <p style="margin-bottom: 16px; color: #606266;">
            将以下链接添加到您的 RSS 阅读器或下载工具中，即可订阅您所有番剧的更新：
          </p>
          <el-input
            v-model="userRssUrl"
            type="textarea"
            :rows="3"
            readonly
            style="margin-bottom: 16px"
          />
          <p v-if="!userRssToken" style="color: #e6a23c; font-size: 12px; margin-bottom: 16px;">
            尚未生成 RSS Token，请点击下方按钮生成
          </p>
          <p v-else style="color: #909399; font-size: 12px; margin-bottom: 16px;">
            如果链接泄露，可以点击"重新生成"按钮获取新链接
          </p>
          <el-button v-if="!userRssToken" type="primary" :loading="rssTokenLoading" @click="handleGenerateUserRssToken">生成 RSS 链接</el-button>
          <template v-else>
            <el-button @click="handleRegenerateUserRssToken" :loading="rssTokenLoading">重新生成</el-button>
            <el-button type="primary" @click="copyUserRssUrl">复制链接</el-button>
          </template>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { userApi, bangumiApi } from '@/api'

interface GlobalFilterData {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

const userStore = useUserStore()
const activeTab = ref('profile')
const dataSource = ref('mikan')
const refreshLoading = ref(false)
const passwordLoading = ref(false)
const filterLoading = ref(false)
const rssTokenLoading = ref(false)
const passwordFormRef = ref<FormInstance>()
const hasGlobalFilter = ref(false)
const showAdvanced = ref(false)
const userRssToken = ref('')
const userRssUrl = ref('')

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const globalFilterForm = reactive({
  include_keywords: [] as string[],
  exclude_keywords: [] as string[],
  subtitle_groups: [] as string[],
  regex_pattern: '',
  min_episode: undefined as number | undefined,
  max_episode: undefined as number | undefined,
})

const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

function parseCommaList(val: string | null): string[] {
  if (!val) return []
  return val.split(',').map(s => s.trim()).filter(Boolean)
}

function buildFilterPayload(): Record<string, unknown> {
  const data: Record<string, unknown> = {}
  if (globalFilterForm.include_keywords.length > 0) {
    data.include_keywords = globalFilterForm.include_keywords.join(',')
  }
  if (globalFilterForm.exclude_keywords.length > 0) {
    data.exclude_keywords = globalFilterForm.exclude_keywords.join(',')
  }
  if (globalFilterForm.subtitle_groups.length > 0) {
    data.subtitle_groups = globalFilterForm.subtitle_groups.join(',')
  }
  if (globalFilterForm.regex_pattern) {
    data.regex_pattern = globalFilterForm.regex_pattern
  }
  if (globalFilterForm.min_episode !== undefined && globalFilterForm.min_episode !== null) {
    data.min_episode = globalFilterForm.min_episode
  }
  if (globalFilterForm.max_episode !== undefined && globalFilterForm.max_episode !== null) {
    data.max_episode = globalFilterForm.max_episode
  }
  return data
}

function loadFilterForm(filter: GlobalFilterData) {
  globalFilterForm.include_keywords = parseCommaList(filter.include_keywords)
  globalFilterForm.exclude_keywords = parseCommaList(filter.exclude_keywords)
  globalFilterForm.subtitle_groups = parseCommaList(filter.subtitle_groups)
  globalFilterForm.regex_pattern = filter.regex_pattern || ''
  globalFilterForm.min_episode = filter.min_episode ?? undefined
  globalFilterForm.max_episode = filter.max_episode ?? undefined
  showAdvanced.value = !!filter.regex_pattern
}

async function fetchGlobalFilter() {
  const response = await userApi.getGlobalFilter()
  if (!response.data) {
    hasGlobalFilter.value = false
    globalFilterForm.include_keywords = []
    globalFilterForm.exclude_keywords = []
    globalFilterForm.subtitle_groups = []
    globalFilterForm.regex_pattern = ''
    globalFilterForm.min_episode = undefined
    globalFilterForm.max_episode = undefined
    showAdvanced.value = false
    return
  }
  loadFilterForm(response.data)
  hasGlobalFilter.value = true
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate()

  passwordLoading.value = true
  try {
    await userApi.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    passwordFormRef.value.resetFields()
  } finally {
    passwordLoading.value = false
  }
}

async function handleRefresh() {
  refreshLoading.value = true
  try {
    await bangumiApi.refresh(dataSource.value)
    ElMessage.success('番剧列表刷新成功')
  } finally {
    refreshLoading.value = false
  }
}

async function handleCreateGlobalFilter() {
  filterLoading.value = true
  try {
    await userApi.createGlobalFilter(buildFilterPayload())
    ElMessage.success('全局过滤器已创建')
    await fetchGlobalFilter()
  } catch {
    // Error handled by interceptor
  } finally {
    filterLoading.value = false
  }
}

async function handleUpdateGlobalFilter() {
  filterLoading.value = true
  try {
    await userApi.updateGlobalFilter(buildFilterPayload())
    ElMessage.success('全局过滤器已更新')
    await fetchGlobalFilter()
  } catch {
    // Error handled by interceptor
  } finally {
    filterLoading.value = false
  }
}

async function handleDeleteGlobalFilter() {
  filterLoading.value = true
  try {
    await userApi.deleteGlobalFilter()
    ElMessage.success('全局过滤器已删除')
    hasGlobalFilter.value = false
    globalFilterForm.include_keywords = []
    globalFilterForm.exclude_keywords = []
    globalFilterForm.subtitle_groups = []
    globalFilterForm.regex_pattern = ''
    globalFilterForm.min_episode = undefined
    globalFilterForm.max_episode = undefined
    showAdvanced.value = false
  } catch {
    // Error handled by interceptor
  } finally {
    filterLoading.value = false
  }
}

function buildUserRssUrl(token: string) {
  const baseUrl = window.location.origin
  const userId = userStore.user?.id ?? 0
  userRssToken.value = token
  userRssUrl.value = `${baseUrl}/api/rss/user/${userId}?token=${token}`
}

async function fetchUserRssToken() {
  try {
    const response = await userApi.getRssToken()
    if (response.data?.rss_token) {
      buildUserRssUrl(response.data.rss_token)
    }
  } catch {
    // Error handled by interceptor
  }
}

async function handleGenerateUserRssToken() {
  rssTokenLoading.value = true
  try {
    const response = await userApi.regenerateRssToken()
    buildUserRssUrl(response.data.rss_token)
    ElMessage.success('RSS 链接已生成')
  } catch {
    // Error handled by interceptor
  } finally {
    rssTokenLoading.value = false
  }
}

async function handleRegenerateUserRssToken() {
  rssTokenLoading.value = true
  try {
    const response = await userApi.regenerateRssToken()
    buildUserRssUrl(response.data.rss_token)
    ElMessage.success('RSS Token 已重新生成')
  } catch {
    // Error handled by interceptor
  } finally {
    rssTokenLoading.value = false
  }
}

async function copyUserRssUrl() {
  try {
    await navigator.clipboard.writeText(userRssUrl.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  fetchGlobalFilter()
  fetchUserRssToken()
})
</script>

<style scoped lang="scss">
.page-header {
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}


</style>
