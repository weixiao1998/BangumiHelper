<template>
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
      <el-option v-for="sg in subtitleGroupOptions" :key="sg" :label="sg" :value="sg" />
    </el-select>
  </el-form-item>

  <el-form-item label="语言">
    <el-select
      v-model="form.language"
      multiple
      filterable
      allow-create
      default-first-option
      placeholder="选择或输入语言"
      style="width: 100%"
    >
      <el-option v-for="lang in languageOptions" :key="lang" :label="lang" :value="lang" />
    </el-select>
  </el-form-item>

  <el-form-item label="集数范围">
    <div class="episode-range">
      <el-input-number v-model="form.min_episode" :min="0" :max="9999" placeholder="最小" controls-position="right" />
      <span>—</span>
      <el-input-number v-model="form.max_episode" :min="0" :max="9999" placeholder="最大" controls-position="right" />
    </div>
  </el-form-item>

  <el-form-item>
    <div class="rule-actions">
      <el-button link type="primary" @click="showAdvanced = !showAdvanced">
        {{ showAdvanced ? '收起高级选项' : '展开高级选项' }}
      </el-button>
      <el-button
        v-if="hasAnyField"
        link
        type="info"
        title="清空所有条件；保存后该规则不过滤"
        @click="clearConditions"
      >
        清空
      </el-button>
    </div>
  </el-form-item>

  <template v-if="showAdvanced">
    <el-form-item label="正则匹配">
      <el-input v-model="form.regex_pattern" placeholder="正则表达式匹配标题" />
    </el-form-item>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { LANGUAGE_OPTION_VALUES } from '@/constants'
import { emptyFilterForm, formHasConditions, type FilterFormData } from '@/utils/filter'

const form = defineModel<FilterFormData>({ required: true })

defineProps<{
  subtitleGroupOptions?: string[]
}>()

const languageOptions = LANGUAGE_OPTION_VALUES
const showAdvanced = ref(Boolean(form.value.regex_pattern))
const hasAnyField = computed(() => formHasConditions(form.value))

watch(
  () => form.value.regex_pattern,
  (value) => {
    if (value) showAdvanced.value = true
  },
)

function clearConditions() {
  form.value = emptyFilterForm()
  showAdvanced.value = false
}
</script>

<style scoped lang="scss">
.rule-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.episode-range {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
