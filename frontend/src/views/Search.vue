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
          <el-button size="small" @click="copyMagnet(row.magnet_url || row.torrent_url)">复制磁力</el-button>
          <el-button v-if="row.torrent_url" size="small" type="primary" @click="openTorrent(row)">下载种子</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { bangumiApi } from '@/api'

interface SearchResult {
  title: string
  episode_number: number
  magnet_url: string
  torrent_url: string
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
  if (!url) {
    ElMessage.warning('该结果没有磁力链接')
    return
  }
  navigator.clipboard.writeText(url)
  ElMessage.success('磁力链接已复制')
}

function openTorrent(row: SearchResult) {
  if (!row.torrent_url) {
    ElMessage.warning('该结果没有种子链接')
    return
  }
  window.open(row.torrent_url, '_blank', 'noopener')
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
