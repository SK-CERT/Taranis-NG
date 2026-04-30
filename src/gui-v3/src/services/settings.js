import { useSettingsStore } from '@/stores/settings'

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
}

export function getSetting(key, def_value = '') {
  const settingsStore = useSettingsStore()

  if (!isInitializedSetting()) {
    console.error('Settings not initialized!', key)
    return def_value || ''
  }

  const settings = settingsStore.getSettings
  if (!Array.isArray(settings)) {
    console.error('Settings is not an array!', key, typeof settings, settings)
    return def_value || ''
  }

  try {
    const setting = settings.find((item) => item && item.key === key)

    if (!setting) {
      console.error('Missing settings key:', key, 'Using default value:', def_value)
      return def_value || ''
    }

    return setting.value !== undefined ? setting.value : def_value || ''
  } catch (error) {
    console.error('Error in getSetting:', key, error, settings)
    return def_value || ''
  }
}

export function getSettingBoolean(key, def_value = false) {
  const val = getSetting(key, def_value ? 'true' : 'false')
  return val != null && val.toLowerCase().trim() === 'true'
}

export function isInitializedSetting() {
  const settingsStore = useSettingsStore()
  const settings = settingsStore.getSettings
  return Array.isArray(settings) && settings.length > 0
}

export function getLocalStorageBoolean(key, def_value = false) {
  const value = localStorage.getItem(key)
  if (value !== null) return value === 'true'
  localStorage.setItem(key, def_value)
  return def_value
}

export default Settings
