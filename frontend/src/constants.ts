// 订阅语言选项, 需与后端 app/core/constants.py 的 LANGUAGE_OPTIONS 保持一致
export interface LanguageOption {
  value: string
  keywords: string[]
}

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  { value: '简体中字', keywords: ['简体', '简中', '简繁', '简日', '中字', 'chs'] },
  { value: '繁体中字', keywords: ['繁体', '繁中', '繁日', 'cts'] },
  { value: '生肉', keywords: ['生肉', 'raw', '无字幕', '無字幕'] },
  { value: '双语字幕', keywords: ['双语', '简繁', '简日', '繁日', '中日'] },
]

export const LANGUAGE_OPTION_VALUES: string[] = LANGUAGE_OPTIONS.map(o => o.value)

export const LANGUAGE_KEYWORDS: Record<string, string[]> = Object.fromEntries(
  LANGUAGE_OPTIONS.map(o => [o.value, o.keywords]),
)
