<template>
  <el-dialog v-model="visible" :title="dialogTitle" width="560px">
    <el-form label-width="100px">
      <el-form-item label="组名称" required>
        <el-input v-model="name" maxlength="50" show-word-limit placeholder="如：2025 追番、补番、本季新番" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input v-model="description" type="textarea" :rows="2" placeholder="可选，仅用于备注" />
      </el-form-item>

      <el-divider content-position="left">组默认过滤规则</el-divider>
      <p class="field-hint">
        组内选择「继承组规则」的订阅会使用这些条件；选择「自定义规则」的订阅不受影响。
        条件全部留空 = 不过滤。
      </p>

      <FilterRuleForm v-model="form" />
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建订阅组' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { groupApi } from '@/api'
import FilterRuleForm from '@/components/FilterRuleForm.vue'
import type { SubscriptionGroup } from '@/types'
import { emptyFilterForm, filterToForm, formToRulePayload, type FilterFormData } from '@/utils/filter'

const props = defineProps<{
  modelValue: boolean
  group?: SubscriptionGroup | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved', group: SubscriptionGroup): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const saving = ref(false)
const name = ref('')
const description = ref('')
const form = ref<FilterFormData>(emptyFilterForm())

const isEdit = computed(() => Boolean(props.group))
const dialogTitle = computed(() => (isEdit.value ? '编辑订阅组' : '新建订阅组'))

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    name.value = props.group?.name || ''
    description.value = props.group?.description || ''
    form.value = props.group ? filterToForm(props.group) : emptyFilterForm()
  },
)

async function handleSave() {
  const trimmedName = name.value.trim()
  if (!trimmedName) {
    ElMessage.warning('请填写订阅组名称')
    return
  }

  const payload = {
    name: trimmedName,
    description: description.value.trim() || null,
    ...formToRulePayload(form.value),
  }

  saving.value = true
  try {
    const response = props.group
      ? await groupApi.update(props.group.id, payload)
      : await groupApi.create(payload)
    ElMessage.success(props.group ? '订阅组已保存' : '订阅组已创建')
    emit('saved', response.data)
    visible.value = false
  } catch {
    // Error handled by interceptor
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.field-hint {
  flex-basis: 100%;
  width: 100%;
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
}
</style>
