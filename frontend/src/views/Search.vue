<template>
  <div class="page-container">
    <div class="page-header">
      <h2>搜索番剧</h2>
    </div>

    <el-form :inline="true" @submit.prevent="handleSearch">
      <el-form-item>
        <el-input v-model="keyword" placeholder="输入关键词搜索" style="width: 400px" clearable />
      </el-form-item>
      <el-form-item>
        <el-select v-model="dataSource" placeholder="数据源" style="width: 150px">
          <el-option label="蜜柑计划" value="mikan" />
          <el-option label="bangumi.moe" value="bangumi_moe" />
          <el-option label="动漫花园" value="dmhy" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSearch">搜索</el-button>
      </el-form-item>
    </el-form>

    <el-skeleton v-if="loading" :rows="10" animated style="margin-top: 20px" />

    <el-empty v-else-if="results.length === 0 && searched" description="未找到相关结果" />

    <el-table v-else-if="results.length > 0" :data="results" style="margin-top: 20px">
      <el-table-column prop="episode_number" label="集数" width="80" />
      <el-table-column prop="title" label="标题" min-width="300">
        <template #default="{ row }">
          <el-tooltip :content="row.title" placement="top">
            <span class="episode-title">{{ row.title }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="subtitle_group" label="字幕组" width="150" />
      <el-table-column label="发布时间" width="180">
        <template #default="{ row }">
          {{ row.publish_time ? dayjs.utc(row.publish_time).local().format('YYYY-MM-DD HH:mm') : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="copyMagnet(row.magnet_url || row.download_url)">复制</el-button>
          <el-button size="small" type="primary" @click="download(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { bangumiApi, downloaderApi } from '@/api'

interface SearchResult {
  title: string
  episode_number: number
  download_url: string
  magnet_url: string
  subtitle_group: string
  publish_time: string
}

const keyword = ref('')
const dataSource = ref('mikan')
const loading = ref(false)
const searched = ref(false)
const results = ref<SearchResult[]>([])

async function handleSearch() {
  if (!keyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  searched.value = true
  try {
    const response = await bangumiApi.search(keyword.value, dataSource.value)
    results.value = response.data
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

function copyMagnet(url: string) {
  navigator.clipboard.writeText(url)
  ElMessage.success('已复制到剪贴板')
}

async function download(row: SearchResult) {
  try {
    const downloadersRes = await downloaderApi.getAll()
    if (downloadersRes.data.length === 0) {
      copyMagnet(row.magnet_url || row.download_url)
      return
    }

    ElMessage.info('请先订阅番剧后再使用下载功能')
  } catch {
    copyMagnet(row.magnet_url || row.download_url)
  }
}
</script>

<style scoped lang="scss">
.page-header {
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}

.episode-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
</style>
