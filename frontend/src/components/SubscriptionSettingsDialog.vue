<template>
  <el-dialog v-model="visible" :title="dialogTitle" width="580px" @close="handleClose">
    <el-form :model="form" label-width="100px">
      <el-form-item label="订阅组">
        <el-select v-model="selectedGroupId" placeholder="选择订阅组" style="width: 100%">
          <el-option
            v-for="group in groups"
            :key="group.id"
            :label="groupOptionLabel(group)"
            :value="group.id"
            :disabled="isGroupDisabled(group)"
          />
        </el-select>
        <div v-if="!selectedGroup || selectedGroup.status === 0" class="field-hint">
          {{ selectedGroup ? '该订阅组已暂停，启用后 RSS 才会输出。' : '请先创建订阅组。' }}
        </div>
      </el-form-item>

      <el-form-item v-if="isEdit" label="订阅状态">
        <el-switch v-model="enabled" active-text="启用" inactive-text="暂停" />
        <div class="field-hint">暂停后该订阅不再出现在组 RSS / 全部 RSS 中，规则与所属组保留。</div>
      </el-form-item>

      <el-form-item label="规则来源">
        <el-radio-group v-model="mode">
          <el-radio value="inherit">继承组默认规则</el-radio>
          <el-radio value="custom">自定义规则</el-radio>
        </el-radio-group>
        <div class="field-hint">
          <template v-if="mode === 'inherit'">
            使用订阅组「{{ selectedGroup?.name || '未选择' }}」的默认规则{{
              groupHasFilter ? '（已设置）' : '（未设置，等同于不过滤）'
            }}。
            <template v-if="hasSavedRule">本订阅已保存的自定义规则会保留但<b>不再生效</b>。</template>
          </template>
          <template v-else>只使用本订阅自己的规则，组规则不参与；条件全部留空即不过滤。</template>
        </div>
      </el-form-item>

      <template v-if="mode === 'custom'">
        <FilterRuleForm v-model="form" :subtitle-group-options="subtitleGroupOptions" />
      </template>
    </el-form>

    <template #footer>
      <el-button v-if="isEdit" type="danger" plain :loading="saving" @click="handleDelete">取消该订阅</el-button>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建订阅' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { subscriptionApi } from '@/api'
import FilterRuleForm from '@/components/FilterRuleForm.vue'
import type { FilterRuleFields, SubscriptionGroup } from '@/types'
import {
  emptyFilterForm,
  filterToForm,
  formToRulePayload,
  ruleHasConditions,
  type FilterFormData,
} from '@/utils/filter'

const props = defineProps<{
  modelValue: boolean
  bangumiId: number
  bangumiName?: string
  // 传入即为编辑模式；为空表示新建订阅
  subscriptionId?: number | null
  // 新建时预选组；编辑时为当前所属组
  groupId?: number | null
  groups: SubscriptionGroup[]
  // 该番剧已订阅的组（用于禁止在同一组重复订阅）
  occupiedGroupIds?: number[]
  status?: number
  filterMode?: string
  filterData?: FilterRuleFields | null
  subtitleGroupOptions?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const saving = ref(false)
const enabled = ref(true)
const mode = ref<'inherit' | 'custom'>('custom')
const selectedGroupId = ref<number | null>(null)
const form = ref<FilterFormData>(emptyFilterForm())

const isEdit = computed(() => Boolean(props.subscriptionId))
const dialogTitle = computed(() => {
  const suffix = props.bangumiName ? ` · ${props.bangumiName}` : ''
  return isEdit.value ? `订阅设置${suffix}` : `新建订阅${suffix}`
})

const selectedGroup = computed(
  () => props.groups.find(group => group.id === selectedGroupId.value) || null,
)
const groupHasFilter = computed(() => ruleHasConditions(selectedGroup.value))
const hasSavedRule = computed(() => ruleHasConditions(props.filterData))

function defaultGroupId(): number | null {
  const occupied = props.occupiedGroupIds || []
  const available = props.groups.find(group => !occupied.includes(group.id))
  return available?.id ?? props.groups[0]?.id ?? null
}

function isGroupDisabled(group: SubscriptionGroup): boolean {
  if (!props.occupiedGroupIds?.includes(group.id)) return false
  // 编辑时当前组必须可再次选中
  return group.id !== props.groupId
}

function groupOptionLabel(group: SubscriptionGroup): string {
  const tags: string[] = []
  if (group.status === 0) tags.push('已暂停')
  if (isGroupDisabled(group)) tags.push('已订阅')
  return tags.length ? `${group.name}（${tags.join('，')}）` : group.name
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return

    selectedGroupId.value = props.groupId ?? defaultGroupId()
    enabled.value = props.status !== 0
    form.value = filterToForm(props.filterData)

    if (isEdit.value) {
      mode.value = props.filterMode === 'custom' ? 'custom' : 'inherit'
    } else {
      // 新建时：组里已配置默认规则则优先继承，否则给自定义表单一个合理默认
      mode.value = groupHasFilter.value ? 'inherit' : 'custom'
    }
  },
)

async function handleSave() {
  if (!selectedGroupId.value) {
    ElMessage.warning('请选择订阅组')
    return
  }

  const payload = formToRulePayload(form.value)
  const hasAnyRule = ruleHasConditions(payload)

  saving.value = true
  try {
    if (!isEdit.value) {
      // 新建：订阅与规则一次提交；自定义模式下不带任何条件即"不过滤"。
      const createFields = hasAnyRule
        ? Object.fromEntries(
            Object.entries(payload).filter(([, value]) => value !== null && value !== undefined && value !== ''),
          )
        : {}
      await subscriptionApi.create({
        bangumi_id: props.bangumiId,
        group_id: selectedGroupId.value,
        filter_mode: mode.value,
        ...(mode.value === 'custom' ? createFields : {}),
      })
      ElMessage.success('订阅成功')
    } else {
      const id = props.subscriptionId as number
      if (mode.value === 'custom') {
        if (hasAnyRule) {
          if (props.filterData) {
            await subscriptionApi.updateFilter(id, payload)
          } else {
            await subscriptionApi.createFilter(id, payload)
          }
        } else if (props.filterData) {
          // 条件被清空：删掉规则行即为"不过滤"
          await subscriptionApi.deleteFilter(id)
        }
      }
      // 模式、状态、所属组单独写；切到 inherit 时订阅自身的规则保留但不生效
      await subscriptionApi.update(id, {
        filter_mode: mode.value,
        status: enabled.value ? 1 : 0,
        group_id: selectedGroupId.value,
      })
      ElMessage.success(
        mode.value === 'custom'
          ? hasAnyRule
            ? '自定义规则已保存并生效'
            : '已保存：该订阅不过滤'
          : '已切换为继承组默认规则',
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

async function handleDelete() {
  const id = props.subscriptionId
  if (!id) return
  try {
    await ElMessageBox.confirm(`确定取消订阅「${props.bangumiName || '该番剧'}」？`, '取消订阅', {
      type: 'warning',
      confirmButtonText: '取消订阅',
      cancelButtonText: '保留',
    })
  } catch {
    return
  }

  saving.value = true
  try {
    await subscriptionApi.delete(id)
    ElMessage.success('取消订阅成功')
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
