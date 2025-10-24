import { store } from '@/store/store'

const Settings = {
    // global settings
    DATE_FORMAT: 'DATE_FORMAT',
    REPORT_SELECTOR_READ_ONLY: 'REPORT_SELECTOR_READ_ONLY',
    TIME_FORMAT: 'TIME_FORMAT',
    // user settings
    DARK_THEME: 'DARK_THEME',
    LANGUAGE: 'LANGUAGE',
    SPELLCHECK: 'SPELLCHECK',
    TAG_COLOR: 'TAG_COLOR',
};

export function getSetting(key, def_value = "") {
    if (!isInitializedSetting) {
        console.error("Settings not inicialized!", key)
        return "";
    }
    var setting = store.getters.getSettings.find(item => item.key === key);
    if (!setting) {
        console.error("Missing settings key:", key, "Using default value:", def_value)
        return def_value;
    }
    console.log("getSetting", key, ":", setting ? setting.value : "")
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
