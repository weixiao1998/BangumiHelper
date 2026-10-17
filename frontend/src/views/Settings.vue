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

      <el-tab-pane v-if="userStore.isAdmin" label="数据管理" name="data">
        <el-card>
          <el-form label-width="100px">
            <el-form-item label="数据源">
              <el-select v-model="dataSource" style="width: 200px">
                <el-option label="蜜柑计划" value="mikan" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="refreshLoading" @click="handleRefresh">刷新番剧列表</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="userStore.isAdmin" label="系统配置" name="system">
        <el-card>
          <el-form :model="systemForm" label-width="140px" style="max-width: 600px">
            <el-form-item label="蜜柑计划地址">
              <el-input v-model="systemForm.mikan_url" placeholder="https://mikanani.me" />
            </el-form-item>
            <el-form-item label="蜜柑账号">
              <el-input v-model="systemForm.mikan_username" placeholder="可选，用于访问需登录资源" />
            </el-form-item>
            <el-form-item label="蜜柑密码">
              <el-input v-model="systemForm.mikan_password" type="password" show-password placeholder="留空表示不修改" />
            </el-form-item>
            <el-form-item label="代理地址">
              <el-input v-model="systemForm.proxy" placeholder="可选，如 http://127.0.0.1:7890" />
            </el-form-item>
            <el-form-item label="注册模式">
              <el-select v-model="systemForm.registration_mode" style="width: 200px">
                <el-option label="开放注册" value="open" />
                <el-option label="关闭注册" value="closed" />
                <el-option label="仅邀请注册" value="invite_only" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="systemLoading" @click="handleUpdateSystem">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="RSS 订阅" name="rss">
        <el-card>
          <p style="margin-bottom: 12px; color: #606266;">
            这是用户级「全部订阅」聚合 RSS：包含所有启用订阅组中的启用订阅。
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
          <p style="color: #909399; font-size: 12px; margin-bottom: 16px;">
            暂停的订阅组与暂停的订阅不会出现在其中；同一番剧在多个组时，同一集会去重。
            feed 默认只输出最近 60 天或 100 条（取先到者）。
          </p>
          <p style="color: #909399; font-size: 12px; margin-bottom: 16px;">
            想按年份/主题分开投放？请到「我的订阅」为每个订阅组单独生成组 RSS。
          </p>
          <el-button v-if="!userRssToken" type="primary" :loading="rssTokenLoading" @click="handleGenerateUserRssToken">生成 RSS 链接</el-button>
          <template v-else>
            <el-button @click="handleRegenerateUserRssToken" :loading="rssTokenLoading">重新生成</el-button>
            <el-button type="primary" @click="copyUserRssUrl">复制链接</el-button>
          </template>
          <el-button link type="primary" style="margin-left: 8px;" @click="goToSubscriptions">去管理订阅组</el-button>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { userApi, bangumiApi, settingsApi, rssApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('profile')
const dataSource = ref('mikan')
const refreshLoading = ref(false)
const passwordLoading = ref(false)
const rssTokenLoading = ref(false)
const passwordFormRef = ref<FormInstance>()
const userRssToken = ref('')
const userRssUrl = ref('')
const systemLoading = ref(false)
const systemForm = reactive({
  mikan_url: '',
  mikan_username: '',
  mikan_password: '',
  proxy: '',
  registration_mode: 'open',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
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

function buildUserRssUrl(token: string) {
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
  const userId = userStore.user?.id ?? 0
  userRssToken.value = token
  userRssUrl.value = `${baseUrl}${rssApi.userFeedUrl(userId)}?token=${token}`
}

function goToSubscriptions() {
  router.push('/subscriptions')
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

async function fetchSystemSettings() {
  try {
    const response = await settingsApi.getSystem()
    const data = response.data
    systemForm.mikan_url = data.mikan_url
    systemForm.mikan_username = data.mikan_username
    systemForm.mikan_password = ''
    systemForm.proxy = data.proxy
    systemForm.registration_mode = data.registration_mode
  } catch {
    // Error handled by interceptor
  }
}

async function handleUpdateSystem() {
  const payload: Record<string, unknown> = {
    mikan_url: systemForm.mikan_url,
    mikan_username: systemForm.mikan_username,
    proxy: systemForm.proxy,
    registration_mode: systemForm.registration_mode,
  }
  if (systemForm.mikan_password) {
    payload.mikan_password = systemForm.mikan_password
  }
  systemLoading.value = true
  try {
    await settingsApi.updateSystem(payload)
    ElMessage.success('系统配置已保存')
    systemForm.mikan_password = ''
  } catch {
    // Error handled by interceptor
  } finally {
    systemLoading.value = false
  }
}

onMounted(() => {
  fetchUserRssToken()
})

watch(() => userStore.isAdmin, (isAdmin) => {
  if (isAdmin) fetchSystemSettings()
}, { immediate: true })
</script>

<style scoped lang="scss">
.page-header {
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}


</style>
