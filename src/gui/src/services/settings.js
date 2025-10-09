import { store } from '@/store/store'

const Settings = {
    // global settings
    DATE_FORMAT: 'DATE_FORMAT',
    REPORT_SELECTOR_READ_ONLY: 'REPORT_SELECTOR_READ_ONLY',
    TIME_FORMAT: 'TIME_FORMAT',
    // user settings
    DARK_THEME: 'DARK_THEME',
    LANGUAGE: 'LANGUAGE',
    NEWS_SHOW_LINK: 'NEWS_SHOW_LINK',
    SPELLCHECK: 'SPELLCHECK',
};

export function getSetting(key, def_value = "") {
    if (!store.getters.getSettings || store.getters.getSettings.length === 0) {
        console.error("Settings not inicialized!")
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
    var val = getSetting(key, def_value)
    return val != null && val.toLowerCase().trim() === "true";
}

export default Settings
