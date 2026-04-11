<template>
  <div class="page-container">
    <div class="page-header">
      <h2>番剧日历</h2>
      <div class="actions">
        <el-select v-model="dataSource" placeholder="选择数据源" style="width: 150px" @change="fetchCalendar">
          <el-option label="蜜柑计划" value="mikan" />
          <el-option label="bangumi.moe" value="bangumi_moe" />
          <el-option label="动漫花园" value="dmhy" />
        </el-select>
        <el-button v-if="userStore.isAdmin" type="primary" :loading="refreshing" @click="refreshCalendar">
          刷新列表
        </el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="10" animated />

    <template v-else>
      <div v-for="day in calendarData" :key="day.weekday" class="weekday-section">
        <h3 class="weekday-title">{{ weekdayNames[day.weekday] || day.weekday }}</h3>
        <div class="card-grid">
          <el-card
            v-for="bangumi in day.bangumi_list"
            :key="bangumi.id"
            class="bangumi-card"
            @click="router.push(`/bangumi/${bangumi.id}`)"
          >
            <img :src="bangumi.cover || '/placeholder.png'" :alt="bangumi.name" class="cover" />
            <div class="info">
              <div class="name" :title="bangumi.name">{{ bangumi.name }}</div>
              <div class="meta">
                <span v-if="bangumi.is_subscribed">已看到第 {{ bangumi.current_episode }} 集</span>
                <span v-else class="unsubscribed">点击查看详情</span>
                <el-tag v-if="bangumi.is_subscribed" type="success" size="small">已订阅</el-tag>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { bangumiApi } from '@/api'
import { useUserStore } from '@/stores/user'

interface BangumiItem {
  id: number
  name: string
  cover: string
  update_time: string
  is_subscribed: boolean
  current_episode: number
}

interface CalendarDay {
  weekday: string
  bangumi_list: BangumiItem[]
}

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const refreshing = ref(false)
const dataSource = ref('mikan')
const calendarData = ref<CalendarDay[]>([])

const weekdayNames: Record<string, string> = {
  sun: '星期日',
  mon: '星期一',
  tue: '星期二',
  wed: '星期三',
  thu: '星期四',
  fri: '星期五',
  sat: '星期六',
  unknown: '未知',
}

async function fetchCalendar() {
  loading.value = true
  try {
    const response = await bangumiApi.getCalendar(dataSource.value)
    calendarData.value = response.data
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function refreshCalendar() {
  refreshing.value = true
  try {
    await bangumiApi.refresh(dataSource.value)
    ElMessage.success('刷新成功')
    await fetchCalendar()
  } catch {
    // Error handled by interceptor
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  fetchCalendar()
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

  .actions {
    display: flex;
    gap: 12px;
  }
}

.unsubscribed {
  color: #909399;
  font-size: 12px;
}
</style>
