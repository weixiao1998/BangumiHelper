import type { FilterRuleFields } from '@/types'

/** 弹窗表单里的过滤规则：多选字段用数组，保存时再拼成逗号分隔串。 */
export interface FilterFormData {
  include_keywords: string[]
  exclude_keywords: string[]
  subtitle_groups: string[]
  language: string[]
  regex_pattern: string
  min_episode?: number
  max_episode?: number
}

export function emptyFilterForm(): FilterFormData {
  return {
    include_keywords: [],
    exclude_keywords: [],
    subtitle_groups: [],
    language: [],
    regex_pattern: '',
    min_episode: undefined,
    max_episode: undefined,
  }
}

export function parseCommaList(val: string | null | undefined): string[] {
  if (!val) return []
  return val
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
}

/** 把后端规则对象载入表单。 */
export function filterToForm(rule: FilterRuleFields | null | undefined): FilterFormData {
  if (!rule) return emptyFilterForm()
  return {
    include_keywords: parseCommaList(rule.include_keywords),
    exclude_keywords: parseCommaList(rule.exclude_keywords),
    subtitle_groups: parseCommaList(rule.subtitle_groups),
    language: parseCommaList(rule.language),
    regex_pattern: rule.regex_pattern || '',
    min_episode: rule.min_episode ?? undefined,
    max_episode: rule.max_episode ?? undefined,
  }
}

/** 把表单转成后端规则字段。始终提交全部字段，清空即显式 null。 */
export function formToRulePayload(form: FilterFormData): FilterRuleFields {
  return {
    include_keywords: form.include_keywords.join(',') || null,
    exclude_keywords: form.exclude_keywords.join(',') || null,
    subtitle_groups: form.subtitle_groups.join(',') || null,
    language: form.language.join(',') || null,
    regex_pattern: form.regex_pattern || null,
    min_episode: form.min_episode ?? null,
    max_episode: form.max_episode ?? null,
  }
}

/** 规则是否真的设置了条件（空规则 = 不过滤）。 */
export function ruleHasConditions(rule: FilterRuleFields | null | undefined): boolean {
  if (!rule) return false
  return Boolean(
    rule.include_keywords ||
      rule.exclude_keywords ||
      rule.subtitle_groups ||
      rule.language ||
      rule.regex_pattern ||
      (rule.min_episode !== null && rule.min_episode !== undefined) ||
      (rule.max_episode !== null && rule.max_episode !== undefined),
  )
}

/** 表单是否有条件；注意数组不能直接用真值判断。 */
export function formHasConditions(form: FilterFormData): boolean {
  return Boolean(
    form.include_keywords.length ||
      form.exclude_keywords.length ||
      form.subtitle_groups.length ||
      form.language.length ||
      form.regex_pattern ||
      form.min_episode !== undefined ||
      form.max_episode !== undefined,
  )
}

/** 番剧 subtitle_groups 形如 "id:名称,id:名称"，侧栏只需要名称。 */
export function parseSubtitleGroups(val: string | null | undefined): string[] {
  if (!val) return []
  return val
    .split(',')
    .map(s => {
      const parts = s.split(':')
      return parts.length > 1 ? parts.slice(1).join(':').trim() : s.trim()
    })
    .filter(Boolean)
}
