export const SETTING_KEYS = [
    'DATE_FORMAT',
    'REPORT_SELECTOR_READ_ONLY',
    'TIME_FORMAT',
    'CONTENT_DEFAULT_LANGUAGE',
    'DARK_THEME',
    'HOTKEYS',
    'SPELLCHECK',
    'TAG_COLOR',
    'UI_LANGUAGE'
] as const

export type SettingKey = (typeof SETTING_KEYS)[number]

export interface SettingEntry {
    key: SettingKey | string
    value: string
}
