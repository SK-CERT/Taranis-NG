import { useSettingsStore } from '@/stores/settings'
import type { SettingEntry, SettingKey } from '@/types/settings'

const Settings = {
    // global settings
    DATE_FORMAT: 'DATE_FORMAT',
    REPORT_SELECTOR_READ_ONLY: 'REPORT_SELECTOR_READ_ONLY',
    TIME_FORMAT: 'TIME_FORMAT',
    // user settings
    CONTENT_DEFAULT_LANGUAGE: 'CONTENT_DEFAULT_LANGUAGE',
    DARK_THEME: 'DARK_THEME',
    HOTKEYS: 'HOTKEYS',
    SPELLCHECK: 'SPELLCHECK',
    TAG_COLOR: 'TAG_COLOR',
    UI_LANGUAGE: 'UI_LANGUAGE'
} as const

export function getSetting(key: SettingKey | string, defValue = ''): string {
    const settingsStore = useSettingsStore()

    if (!isInitializedSetting()) {
        console.error('Settings not initialized!', key)
        return defValue || ''
    }

    const settings = settingsStore.getSettings
    if (!Array.isArray(settings)) {
        console.error('Settings is not an array!', key, typeof settings, settings)
        return defValue || ''
    }

    try {
        const setting = settings.find((item) => item && item.key === key)

        if (!setting) {
            console.error('Missing settings key:', key, 'Using default value:', defValue)
            return defValue || ''
        }

        return setting.value !== undefined ? setting.value : defValue || ''
    } catch (error) {
        console.error('Error in getSetting:', key, error, settings)
        return defValue || ''
    }
}

export function getSettingBoolean(key: SettingKey | string, defValue = false): boolean {
    const val = getSetting(key, defValue ? 'true' : 'false')
    return val != null && val.toLowerCase().trim() === 'true'
}

export function isInitializedSetting(): boolean {
    const settingsStore = useSettingsStore()
    const settings = settingsStore.getSettings
    return Array.isArray(settings) && settings.length > 0
}

export function getLocalStorageBoolean(key: string, defValue = false): boolean {
    const value = localStorage.getItem(key)
    if (value !== null) return value === 'true'
    localStorage.setItem(key, String(defValue))
    return defValue
}

export default Settings
