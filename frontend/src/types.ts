/** 过滤规则字段：组默认规则与订阅自定义规则共用同一形状。 */
export interface FilterRuleFields {
  include_keywords: string | null
  exclude_keywords: string | null
  subtitle_groups: string | null
  language: string | null
  regex_pattern: string | null
  min_episode: number | null
  max_episode: number | null
}

/** 订阅响应里嵌套的组摘要。 */
export interface SubscriptionGroupBrief {
  id: number
  name: string
  status: number
}

/** 订阅组完整信息（含组默认规则与组 RSS token）。 */
export interface SubscriptionGroup extends FilterRuleFields {
  id: number
  user_id: number
  name: string
  description: string | null
  status: number
  rss_token: string | null
  created_at: string
  updated_at: string
}

/** 订阅关联的番剧摘要。 */
export interface SubscriptionBangumi {
  id: number
  name: string
  cover: string
  subtitle_groups?: string | null
}

/** 一条番剧订阅。 */
export interface Subscription {
  id: number
  user_id: number
  group_id: number
  status: number
  filter_mode: 'inherit' | 'custom' | string
  group: SubscriptionGroupBrief
  bangumi: SubscriptionBangumi
  filter: FilterRuleFields | null
}
