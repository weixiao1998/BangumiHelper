<template>
  <el-dialog v-model="visible" :title="dialogTitle" width="560px" @close="handleClose">
    <el-form :model="form" label-width="100px">
      <el-form-item v-if="isEdit" label="订阅状态">
        <el-switch v-model="enabled" active-text="启用" inactive-text="暂停" />
        <div class="field-hint">暂停后该订阅不再出现在 RSS 中，过滤规则与配置保留。</div>
      </el-form-item>

      <el-form-item label="规则来源">
        <el-radio-group v-model="mode">
          <el-radio value="inherit">继承全局默认规则</el-radio>
          <el-radio value="custom">自定义规则</el-radio>
        </el-radio-group>
        <div class="field-hint">
          <template v-if="mode === 'inherit'">
            全局默认规则{{ hasGlobalFilter ? '已设置' : '未设置（等同于不过滤）' }}。
            <template v-if="hasSavedRule">本订阅已保存的自定义规则会被保留但<b>不再生效</b>。</template>
          </template>
          <template v-else>只使用本订阅的规则，全局规则不参与；条件全部留空即不过滤。</template>
        </div>
      </el-form-item>

      <template v-if="mode === 'custom'">
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
          <div style="display: flex; align-items: center; gap: 8px;">
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
              title="清空所有条件；保存后该订阅不过滤"
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
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建订阅' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { subscriptionApi } from '@/api'
import { LANGUAGE_OPTION_VALUES } from '@/constants'

interface FilterData {
  include_keywords: string[]
  exclude_keywords: string[]
  subtitle_groups: string[]
  language: string[]
  regex_pattern: string
  min_episode: number | undefined
  max_episode: number | undefined
}

interface FilterSource {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  language: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

/**
 * 订阅设置：新建订阅与编辑订阅共用同一个弹窗。
 * 此前「订阅设置」（详情页内联、仅未订阅可见）与「订阅过滤器」（独立组件、仅已订阅可见）
 * 是同一份配置的两套界面，字段与能力都不一致，详见 documents/filter-redesign.md。
 */
const props = defineProps<{
  modelValue: boolean
  bangumiId: number
  bangumiName?: string
  // 传入即为编辑模式；为空表示新建订阅
  subscriptionId?: number | null
  status?: number
  filterMode?: string
  hasGlobalFilter?: boolean
  filterData?: FilterSource | null
  subtitleGroupOptions?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const saving = ref(false)
const showAdvanced = ref(false)
const mode = ref<'inherit' | 'custom'>('custom')
const enabled = ref(true)

const isEdit = computed(() => !!props.subscriptionId)
const dialogTitle = computed(() => (props.bangumiName ? `订阅设置 · ${props.bangumiName}` : '订阅设置'))

function parseCommaList(val: string | null | undefined): string[] {
  if (!val) return []
  return val.split(',').map(s => s.trim()).filter(Boolean)
}

const form = ref<FilterData>({
  include_keywords: [],
  exclude_keywords: [],
  subtitle_groups: [],
  language: [],
  regex_pattern: '',
  min_episode: undefined,
  max_episode: undefined,
})

const languageOptions = LANGUAGE_OPTION_VALUES

watch(() => props.modelValue, (val) => {
  if (!val) return

  // 打开时同步：规则来源、订阅状态、已有的自定义规则。
  // 新建订阅一律默认「自定义规则」——filterMode 只对编辑模式有意义，
  // 不能因为父组件顺手传了个 'inherit' 就被覆盖（踩过这个坑）。
  if (!isEdit.value) {
    mode.value = 'custom'
  } else {
    mode.value = props.filterMode === 'custom' ? 'custom' : 'inherit'
  }
  enabled.value = props.status !== 0

  if (props.filterData) {
    form.value = {
      include_keywords: parseCommaList(props.filterData.include_keywords),
      exclude_keywords: parseCommaList(props.filterData.exclude_keywords),
      subtitle_groups: parseCommaList(props.filterData.subtitle_groups),
      language: parseCommaList(props.filterData.language),
      regex_pattern: props.filterData.regex_pattern || '',
      min_episode: props.filterData.min_episode ?? undefined,
      max_episode: props.filterData.max_episode ?? undefined,
    }
    showAdvanced.value = !!props.filterData.regex_pattern
  } else {
    form.value = {
      include_keywords: [],
      exclude_keywords: [],
      subtitle_groups: [],
      language: [],
      regex_pattern: '',
      min_episode: undefined,
      max_episode: undefined,
    }
    showAdvanced.value = false
  }
})

type RulePayload = ReturnType<typeof buildRulePayload>

function ruleHasConditions(rule: RulePayload | FilterSource | null | undefined): boolean {
  if (!rule) return false
  return Boolean(
    rule.include_keywords ||
      rule.exclude_keywords ||
      rule.subtitle_groups ||
      rule.language ||
      rule.regex_pattern ||
      rule.min_episode !== null && rule.min_episode !== undefined ||
      rule.max_episode !== null && rule.max_episode !== undefined,
  )
}

// 已保存的规则必须"真的有条件"才算数（空规则 == 没有规则 == 不过滤）
const hasSavedRule = computed(() => ruleHasConditions(props.filterData))
const hasAnyField = computed(() => ruleHasConditions(buildRulePayload()))

function clearConditions() {
  form.value = {
    include_keywords: [],
    exclude_keywords: [],
    subtitle_groups: [],
    language: [],
    regex_pattern: '',
    min_episode: undefined,
    max_episode: undefined,
  }
  showAdvanced.value = false
}

function buildRulePayload() {
  // 始终提交所有字段：清空(取消选择)的字段以 null 提交，后端才会将其重置
  return {
    include_keywords: form.value.include_keywords.join(',') || null,
    exclude_keywords: form.value.exclude_keywords.join(',') || null,
    subtitle_groups: form.value.subtitle_groups.join(',') || null,
    language: form.value.language.join(',') || null,
    regex_pattern: form.value.regex_pattern || null,
    min_episode: form.value.min_episode ?? null,
    max_episode: form.value.max_episode ?? null,
  }
}

async function handleSave() {
  const rule = buildRulePayload()
  const hasAnyRule = ruleHasConditions(rule)

  saving.value = true
  try {
    if (!isEdit.value) {
      // 新建：订阅与规则一次提交；自定义模式下不带任何条件即"不过滤"。
      const createFields = hasAnyRule
        ? Object.fromEntries(Object.entries(rule).filter(([, v]) => v !== null && v !== undefined && v !== ''))
        : {}
      await subscriptionApi.create({
        bangumi_id: props.bangumiId,
        filter_mode: mode.value,
        ...(mode.value === 'custom' ? createFields : {}),
      })
      ElMessage.success('订阅成功')
    } else {
      const id = props.subscriptionId as number
      if (mode.value === 'custom') {
        if (hasAnyRule) {
          if (props.filterData) {
            await subscriptionApi.updateFilter(id, rule)
          } else {
            await subscriptionApi.createFilter(id, rule)
          }
        } else if (props.filterData) {
          // 条件被清空：删掉规则行即为"不过滤"（不再需要单独的删除按钮）
          await subscriptionApi.deleteFilter(id)
        }
      }
      // 模式与状态单独写：切到 inherit 时订阅自身的规则保留但不生效
      await subscriptionApi.update(id, { filter_mode: mode.value, status: enabled.value ? 1 : 0 })
      ElMessage.success(
        mode.value === 'custom'
          ? hasAnyRule
            ? '自定义规则已保存并生效'
            : '已保存：该订阅不过滤'
          : '已切换为继承全局默认规则',
      )
    }
    emit('saved')
    visible.value = false
  } catch {
    // Error handled by interceptor
  } finally {
    saving.value = false
  }
}

function handleClose() {
  visible.value = false
}
</script>

<style scoped lang="scss">
.rule-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.field-hint {
  // el-form-item__content 是 flex-wrap 容器，div 默认会和控件并排；
  // flex-basis: 100% 让它稳定换到下一行
  flex-basis: 100%;
  width: 100%;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
}
</style>
