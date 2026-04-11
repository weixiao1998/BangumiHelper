<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>注册账号</h2>
          <p>{{ registrationConfig.message }}</p>
        </div>
      </template>

      <el-alert
        v-if="registrationConfig.mode === 'closed'"
        title="注册已关闭"
        type="error"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #default>
          管理员已关闭注册功能，请联系管理员获取账号
        </template>
      </el-alert>

      <el-form 
        v-if="registrationConfig.mode !== 'closed'"
        ref="formRef" 
        :model="form" 
        :rules="rules" 
        label-width="0"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>

        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱" prefix-icon="Message" size="large" />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item v-if="registrationConfig.mode === 'invite_only'" prop="inviteCode">
          <el-input
            v-model="form.inviteCode"
            placeholder="邀请码"
            prefix-icon="Ticket"
            size="large"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="handleRegister">
            注册
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button text type="primary" @click="router.push('/login')">
            已有账号？立即登录
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="registrationConfig.mode === 'closed'" style="text-align: center">
        <el-button text type="primary" @click="router.push('/login')">
          返回登录
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const registrationConfig = ref({ mode: 'open', message: '创建您的追番助手账号' })

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: '',
})

const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
  inviteCode: [
    { required: true, message: '请输入邀请码', trigger: 'blur' },
  ],
}

async function fetchRegistrationConfig() {
  try {
    const response = await authApi.getRegistrationConfig()
    registrationConfig.value = response.data
  } catch {
    // Use default config
  }
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.register(form.username, form.email, form.password, form.inviteCode)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRegistrationConfig()
})
</script>

<style scoped lang="scss">
.register-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 400px;

  .card-header {
    text-align: center;

    h2 {
      margin: 0;
      font-size: 28px;
      color: #303133;
    }

    p {
      margin: 8px 0 0;
      color: #909399;
    }
  }
}
</style>
