import { store } from '@/store/store'

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
    UI_LANGUAGE: 'UI_LANGUAGE',
};

export function getSetting(key, def_value = "") {
    if (!isInitializedSetting) {
        // eslint-disable-next-line no-console
        console.error("Settings not inicialized!", key)
        return "";
    }
    var setting = store.getters.getSettings.find(item => item.key === key);
    if (!setting) {
        // eslint-disable-next-line no-console
        console.error("Missing settings key:", key, "Using default value:", def_value)
        return def_value;
    }
    // console.log("getSetting", key, ":", setting ? setting.value : "")
    return setting ? setting.value : "";
}

export function getSettingBoolean(key, def_value = false) {
    var val = getSetting(key, def_value ? "true" : "false")
    return val != null && val.toLowerCase().trim() === "true";
}

export function isInitializedSetting() {
    return (store.getters.getSettings && store.getters.getSettings.length > 0)
}

export function getLocalStorageBoolean(key, def_value = false) {
    const value = localStorage.getItem(key)
    if (value !== null) return value === "true";
    localStorage.setItem(key, def_value);
    return def_value;
}

export default Settings
