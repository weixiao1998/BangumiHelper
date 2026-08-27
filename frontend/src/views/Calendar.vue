<template>
  <div class="page-container">
    <div class="page-header">
      <h2>番剧日历</h2>
      <div class="actions">
        <el-select v-model="dataSource" placeholder="选择数据源" style="width: 150px" @change="fetchCalendar">
          <el-option label="蜜柑计划" value="mikan" />
        </el-select>
        <el-select v-model="year" placeholder="年份" style="width: 110px" @change="fetchCalendar">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>
        <el-select v-model="season" placeholder="季度" style="width: 110px" @change="fetchCalendar">
          <el-option v-for="s in seasonOptions" :key="s.value" :label="s.label" :value="s.value" />
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
            <img :src="bangumi.cover || '/placeholder.png'" :alt="bangumi.name" class="cover" @error="onImgError" />
            <div class="info">
              <div class="name" :title="bangumi.name">{{ bangumi.name }}</div>
              <div class="meta">
                <el-tag v-if="bangumi.is_subscribed" type="success" size="small">已订阅</el-tag>
                <el-tag v-if="bangumi.seasons && bangumi.seasons.length" type="info" size="small">{{ formatSeasons(bangumi.seasons) }}</el-tag>
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
  seasons: string[]
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

const year = ref(new Date().getFullYear())
const season = ref(currentSeasonFromDate())
const yearOptions = buildYearOptions()
const seasonOptions = [
  { value: '春', label: '春季' },
  { value: '夏', label: '夏季' },
  { value: '秋', label: '秋季' },
  { value: '冬', label: '冬季' },
]

const seasonOrder = ['春', '夏', '秋', '冬']

// 把 ["2026 夏", "2026 春"] 合并成一个紧凑标签 "2026 春·夏"，
// 年番跨多季时如 "2025 春·夏·秋·冬 / 2026 春·夏"。
function formatSeasons(seasons: string[]): string {
  const byYear: Record<number, string[]> = {}
  for (const s of seasons) {
    const m = s.match(/^(\d{4})\s+(春|夏|秋|冬)$/)
    if (!m) continue
    const y = Number(m[1])
    const q = m[2]
    ;(byYear[y] ||= []).push(q)
  }
  return Object.keys(byYear)
    .sort((a, b) => Number(a) - Number(b))
    .map((y) => {
      const qs = byYear[Number(y)].sort((a, b) => seasonOrder.indexOf(a) - seasonOrder.indexOf(b))
      return `${y} ${qs.join('·')}`
    })
    .join(' / ')
}

function currentSeasonFromDate(): string {
  const m = new Date().getMonth() + 1
  if (m >= 1 && m <= 3) return '冬'
  if (m >= 4 && m <= 6) return '春'
  if (m >= 7 && m <= 9) return '夏'
  return '秋'
}

function buildYearOptions(): number[] {
  const now = new Date().getFullYear()
  const list: number[] = []
  for (let y = now; y >= now - 6; y--) list.push(y)
  return list
}

const weekdayNames: Record<string, string> = {
  sun: '星期日',
  mon: '星期一',
  tue: '星期二',
  wed: '星期三',
  thu: '星期四',
  fri: '星期五',
  sat: '星期六',
  movie: '剧场版',
  ova: 'OVA',
  unknown: '未知',
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  if (img.src.includes('/placeholder.png')) return
  img.src = '/placeholder.png'
}

async function fetchCalendar() {
  loading.value = true
  try {
    const response = await bangumiApi.getCalendar(dataSource.value, year.value, season.value)
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
    await bangumiApi.refresh(dataSource.value, year.value, season.value)
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
</style>
