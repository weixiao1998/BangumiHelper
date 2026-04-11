<template>
  <div class="page-container">
    <div class="page-header">
      <h2>下载器管理</h2>
      <el-button type="primary" @click="showDialog()">添加下载器</el-button>
    </div>

    <el-table :data="downloaders" v-loading="loading">
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column prop="downloader_type" label="类型" width="120">
        <template #default="{ row }">
          <el-tag>{{ getTypeName(row.downloader_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="地址" min-width="200">
        <template #default="{ row }">
          {{ row.host }}:{{ row.port }}
        </template>
      </el-table-column>
      <el-table-column prop="is_default" label="默认" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success">是</el-tag>
          <el-tag v-else type="info">否</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="testConnection(row)">测试</el-button>
          <el-button size="small" @click="showDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑下载器' : '添加下载器'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="输入下载器名称" />
        </el-form-item>
        <el-form-item label="类型" prop="downloader_type">
          <el-select v-model="form.downloader_type" placeholder="选择下载器类型" style="width: 100%">
            <el-option label="qBittorrent" value="qbittorrent" />
            <el-option label="Transmission" value="transmission" />
            <el-option label="Aria2" value="aria2" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机地址" prop="host">
          <el-input v-model="form.host" placeholder="如: 127.0.0.1" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="可选" show-password />
        </el-form-item>
        <el-form-item v-if="form.downloader_type === 'aria2'" label="RPC路径">
          <el-input v-model="form.rpc_url" placeholder="/jsonrpc" />
        </el-form-item>
        <el-form-item v-if="form.downloader_type === 'aria2'" label="Token">
          <el-input v-model="form.token" placeholder="可选" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { downloaderApi } from '@/api'

interface Downloader {
  id: number
  name: string
  downloader_type: string
  host: string
  port: number
  username: string
  password: string
  rpc_url: string
  token: string
  is_default: boolean
}

const loading = ref(false)
const downloaders = ref<Downloader[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  downloader_type: 'qbittorrent',
  host: '127.0.0.1',
  port: 8080,
  username: '',
  password: '',
  rpc_url: '/jsonrpc',
  token: '',
  is_default: false,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  downloader_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
}

const typeNames: Record<string, string> = {
  qbittorrent: 'qBittorrent',
  transmission: 'Transmission',
  aria2: 'Aria2',
}

function getTypeName(type: string) {
  return typeNames[type] || type
}

async function fetchDownloaders() {
  loading.value = true
  try {
    const response = await downloaderApi.getAll()
    downloaders.value = response.data
  } finally {
    loading.value = false
  }
}

function showDialog(downloader?: Downloader) {
  if (downloader) {
    isEdit.value = true
    editingId.value = downloader.id
    Object.assign(form, downloader)
  } else {
    isEdit.value = false
    editingId.value = null
    Object.assign(form, {
      name: '',
      downloader_type: 'qbittorrent',
      host: '127.0.0.1',
      port: 8080,
      username: '',
      password: '',
      rpc_url: '/jsonrpc',
      token: '',
      is_default: false,
    })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    if (isEdit.value && editingId.value) {
      await downloaderApi.update(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await downloaderApi.create(form)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchDownloaders()
  } finally {
    submitting.value = false
  }
}

async function testConnection(downloader: Downloader) {
  try {
    await downloaderApi.test(downloader.id)
    ElMessage.success('连接成功')
  } catch {
    // Error handled by interceptor
  }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确定要删除这个下载器吗？', '提示', { type: 'warning' })
  await downloaderApi.delete(id)
  ElMessage.success('删除成功')
  fetchDownloaders()
}

onMounted(() => {
  fetchDownloaders()
})
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}
</style>
