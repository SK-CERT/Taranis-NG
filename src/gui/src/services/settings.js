import { store } from '@/store/store'

const Settings = {
    DATE_FORMAT: 'DATE_FORMAT',
    TIME_FORMAT: 'TIME_FORMAT',
    REPORT_SELECTOR_READ_ONLY: 'REPORT_SELECTOR_READ_ONLY',
};

export function getSetting(key) {
    if (!store.getters.getSettings.items || store.getters.getSettings.items.length === 0) {
        console.error("Settings not inicialized!")
        return "";
    }
    const setting = store.getters.getSettings.items.find(item => item.key === key);
    if (!setting) {
        console.error("Missing settings key:", key)
        return "";
    }
    console.log("getSetting:", setting ? setting.value : "")
    return setting ? setting.value : "";
}

export function getSettingBoolean(key) {
    var val = getSetting(key)
    return (val != null && val.toLowerCase().trim() === "true") ? true : false
}


export default Settings
