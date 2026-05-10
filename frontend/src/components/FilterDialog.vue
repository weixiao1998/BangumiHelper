<template>
  <el-dialog v-model="visible" title="订阅过滤器" width="560px" @close="handleClose">
    <el-form :model="form" label-width="100px">
      <el-form-item label="包含关键词">
        <el-select
          v-model="form.include_keywords"
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
          v-model="form.exclude_keywords"
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
          v-model="form.subtitle_groups"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="subtitleGroupOptions?.length ? '选择或输入字幕组' : '输入字幕组名称后回车添加'"
          style="width: 100%"
        >
          <el-option
            v-for="sg in subtitleGroupOptions"
            :key="sg"
            :label="sg"
            :value="sg"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="集数范围">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-input-number v-model="form.min_episode" :min="0" :max="9999" placeholder="最小" controls-position="right" />
          <span>—</span>
          <el-input-number v-model="form.max_episode" :min="0" :max="9999" placeholder="最大" controls-position="right" />
        </div>
      </el-form-item>

      <el-form-item>
        <el-button link type="primary" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? '收起高级选项' : '展开高级选项' }}
        </el-button>
      </el-form-item>

      <template v-if="showAdvanced">
        <el-form-item label="正则匹配">
          <el-input v-model="form.regex_pattern" placeholder="正则表达式匹配标题" />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button v-if="isEdit" type="danger" @click="handleDelete">删除过滤器</el-button>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { subscriptionApi } from '@/api'

interface FilterData {
  include_keywords: string[]
  exclude_keywords: string[]
  subtitle_groups: string[]
  regex_pattern: string
  min_episode: number | undefined
  max_episode: number | undefined
}

const props = defineProps<{
  modelValue: boolean
  subscriptionId: number
  filterData?: {
    include_keywords: string | null
    exclude_keywords: string | null
    subtitle_groups: string | null
    regex_pattern: string | null
    min_episode: number | null
    max_episode: number | null
  } | null
  subtitleGroupOptions?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
  (e: 'deleted'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const saving = ref(false)
const showAdvanced = ref(false)

const isEdit = computed(() => !!props.filterData)

function parseCommaList(val: string | null): string[] {
  if (!val) return []
  return val.split(',').map(s => s.trim()).filter(Boolean)
}

const form = ref<FilterData>({
  include_keywords: [],
  exclude_keywords: [],
  subtitle_groups: [],
  regex_pattern: '',
  min_episode: undefined,
  max_episode: undefined,
})

watch(() => props.modelValue, (val) => {
  if (val && props.filterData) {
    form.value = {
      include_keywords: parseCommaList(props.filterData.include_keywords),
      exclude_keywords: parseCommaList(props.filterData.exclude_keywords),
      subtitle_groups: parseCommaList(props.filterData.subtitle_groups),
      regex_pattern: props.filterData.regex_pattern || '',
      min_episode: props.filterData.min_episode ?? undefined,
      max_episode: props.filterData.max_episode ?? undefined,
    }
    showAdvanced.value = !!props.filterData.regex_pattern
  } else if (val) {
    form.value = {
      include_keywords: [],
      exclude_keywords: [],
      subtitle_groups: [],
      regex_pattern: '',
      min_episode: undefined,
      max_episode: undefined,
    }
    showAdvanced.value = false
  }
})

function buildPayload() {
  const data: Record<string, unknown> = {}
  if (form.value.include_keywords.length > 0) {
    data.include_keywords = form.value.include_keywords.join(',')
  }
  if (form.value.exclude_keywords.length > 0) {
    data.exclude_keywords = form.value.exclude_keywords.join(',')
  }
  if (form.value.subtitle_groups.length > 0) {
    data.subtitle_groups = form.value.subtitle_groups.join(',')
  }
  if (form.value.regex_pattern) {
    data.regex_pattern = form.value.regex_pattern
  }
  if (form.value.min_episode !== undefined && form.value.min_episode !== null) {
    data.min_episode = form.value.min_episode
  }
  if (form.value.max_episode !== undefined && form.value.max_episode !== null) {
    data.max_episode = form.value.max_episode
  }
  return data
}

async function handleSave() {
  saving.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await subscriptionApi.updateFilter(props.subscriptionId, payload)
      ElMessage.success('过滤器已更新')
    } else {
      await subscriptionApi.createFilter(props.subscriptionId, payload)
      ElMessage.success('过滤器已创建')
    }
    emit('saved')
    visible.value = false
  } catch {
    // Error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确定要删除此过滤器吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await subscriptionApi.deleteFilter(props.subscriptionId)
    ElMessage.success('过滤器已删除')
    emit('deleted')
    visible.value = false
  } catch {
    // cancelled or error handled by interceptor
  }
}

function handleClose() {
  visible.value = false
}
</script>


