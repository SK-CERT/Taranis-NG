import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getUserWordLists, getAvailableWordLists, updateUserWordLists, getHotkeys, updateHotkeys } from '@/api/user'
import { getAllSettings, updateSetting } from '@/api/config'
import { Settings, HotkeyAction, type SettingEntry, type SettingKey, type HotkeyActionType } from '@/types/settings'

type HotkeyEntry = {
    key: string
    alias: HotkeyActionType
    icon: string
}

type SearchFilter = {
    search: string
}

type SaveSettingsPayload = {
    data: { id?: string | number; [key: string]: unknown }
    is_global: boolean
}

type ApiResponse<T> = {
    data?: T
}

const asObjectWithItems = (value: unknown): { items?: unknown[] } | null => {
    if (value && typeof value === 'object') {
        return value as { items?: unknown[] }
    }
    return null
}

// This does not work completely because we also return additional database fields. It is not a pure SettingEntry type, but it works
const toSettingEntries = (value: unknown): SettingEntry[] => {
    if (Array.isArray(value)) {
        return value as SettingEntry[]
    }

    const withItems = asObjectWithItems(value)
    if (withItems && Array.isArray(withItems.items)) {
        return withItems.items as SettingEntry[]
    }

    return []
}

export const useSettingsStore = defineStore('settings', () => {
    // State
    const settings = ref<SettingEntry[]>([])
    const spellcheck = ref(true)
    const hotkeys = ref<HotkeyEntry[]>([])
    const word_lists = ref<unknown[]>([])
    const available_word_lists = ref<unknown[]>([])

    // Getters
    const getSettings = computed(() => (Array.isArray(settings.value) ? settings.value : []))

    const getProfileHotkeys = computed(() => (Array.isArray(hotkeys.value) ? hotkeys.value : []))

    const getProfileWordLists = computed(() => (Array.isArray(word_lists.value) ? word_lists.value : []))

    const getAvailableWordListsComputed = computed(() => (Array.isArray(available_word_lists.value) ? available_word_lists.value : []))

    const getProfileLanguage = computed(() => {
        // Use internal getSetting to avoid circular dependency
        const settingsArray = Array.isArray(settings.value) ? settings.value : []
        const uiLangSetting = settingsArray.find((item) => item.key === Settings.UI_LANGUAGE)
        let lng = uiLangSetting ? uiLangSetting.value : null

        if (!lng) {
            lng = navigator.language.split('-')[0] || null
        }
        if (!lng && typeof import.meta.env.VITE_APP_TARANIS_NG_LOCALE !== 'undefined') {
            lng = import.meta.env.VITE_APP_TARANIS_NG_LOCALE || null
        }
        if (!lng) {
            lng = 'en'
        }
        return lng
    })

    const getDateTimeFormat = computed(() => {
        const dateFmt = getSetting(Settings.DATE_FORMAT, 'yyyy-MM-dd')
        const timeFmt = getSetting(Settings.TIME_FORMAT, 'HH:mm')
        if (dateFmt != '' && timeFmt != '') {
            return dateFmt + ' ' + timeFmt
        }
        return 'yyyy-MM-dd HH:mm'
    })

    // Actions
    function getSetting(key: SettingKey, defValue = ''): string {
        try {
            const settingsArray = Array.isArray(settings.value) ? settings.value : []
            if (settingsArray.length === 0) return defValue || ''
            if (typeof settingsArray.find !== 'function') {
                console.error('[Settings] settingsArray.find is not a function:', typeof settingsArray, settingsArray)
                return defValue || ''
            }
            const setting = settingsArray.find((s) => s && s.key === key)
            if (!setting) {
                console.error('[Settings] missing key:', key, 'Using default value:', defValue)
                return defValue || ''
            }
            return setting.value !== undefined ? setting.value : defValue || ''
        } catch (error) {
            console.error('[Settings] Error in getSetting:', key, error)
            return defValue || ''
        }
    }

    function getSettingBoolean(key: SettingKey, defValue = false): boolean {
        const val = getSetting(key, defValue ? 'true' : 'false')
        return val != null && val.toLowerCase().trim() === 'true'
    }

    async function loadSettings(data: SearchFilter): Promise<ApiResponse<unknown>> {
        try {
            const response = (await getAllSettings(data)) as ApiResponse<unknown>
            // Ensure we always set an array
            const responseData = response?.data

            settings.value = toSettingEntries(responseData)
            if (settings.value.length === 0) {
                console.warn('[Settings] Unexpected response format, setting to empty array')
            }
            return response
        } catch (error) {
            console.error('[Settings] Error loading settings:', error)
            settings.value = []
            throw error
        }
    }

    async function saveSettings({ data, is_global }: SaveSettingsPayload): Promise<ApiResponse<unknown>> {
        const response = (await updateSetting(data, is_global)) as ApiResponse<unknown>
        // Ensure we always set an array
        const responseData = response?.data
        settings.value = toSettingEntries(responseData)
        return response
    }

    async function loadUserWordLists(): Promise<ApiResponse<unknown>> {
        try {
            const response = (await getUserWordLists()) as ApiResponse<unknown>
            const responseData = response?.data

            word_lists.value = Array.isArray(responseData) ? responseData : []
            return response
        } catch (error) {
            console.error('[Settings] Error loading word lists:', error)
            word_lists.value = []
            throw error
        }
    }

    async function loadAvailableWordLists(data: SearchFilter): Promise<ApiResponse<unknown>> {
        try {
            const response = (await getAvailableWordLists(data)) as ApiResponse<unknown>
            const responseData = response?.data
            const withItems = asObjectWithItems(responseData)

            if (withItems && Array.isArray(withItems.items)) {
                available_word_lists.value = withItems.items
            } else if (Array.isArray(responseData)) {
                available_word_lists.value = responseData
            } else {
                available_word_lists.value = []
            }
            return response
        } catch (error) {
            console.error('[Settings] Error loading available word lists:', error)
            available_word_lists.value = []
            throw error
        }
    }

    async function saveUserWordLists(data: unknown): Promise<ApiResponse<unknown>> {
        try {
            const response = (await updateUserWordLists(data)) as ApiResponse<unknown>
            const responseData = response?.data
            word_lists.value = Array.isArray(responseData) ? responseData : []
            return response
        } catch (error) {
            console.error('[Settings] Error saving word lists:', error)
            throw error
        }
    }

    async function loadUserHotkeys(): Promise<ApiResponse<unknown>> {
        try {
            const response = (await getHotkeys()) as ApiResponse<unknown>
            const responseData = response?.data

            setUserHotkeys(Array.isArray(responseData) ? (responseData as HotkeyEntry[]) : [])
            return response
        } catch (error) {
            console.error('[Settings] Error loading hotkeys:', error)
            setUserHotkeys([])
            throw error
        }
    }

    async function saveUserHotkeys(data: unknown): Promise<ApiResponse<unknown>> {
        try {
            const response = (await updateHotkeys(data)) as ApiResponse<unknown>
            const responseData = response?.data
            setUserHotkeys(Array.isArray(responseData) ? (responseData as HotkeyEntry[]) : [])
            return response
        } catch (error) {
            console.error('[Settings] Error saving hotkeys:', error)
            throw error
        }
    }

    function setUserHotkeys(userHotkeys: HotkeyEntry[]): void {
        try {
            resetHotkeys()
            if (!Array.isArray(userHotkeys)) {
                console.warn('[Settings] userHotkeys is not an array:', typeof userHotkeys)
                return
            }

            if (!Array.isArray(hotkeys.value)) {
                console.error('[Settings] hotkeys.value is not an array after reset!:', typeof hotkeys.value)
                resetHotkeys()
            }

            for (let i = 0; i < hotkeys.value.length; i++) {
                for (let j = 0; j < userHotkeys.length; j++) {
                    const hotkey = hotkeys.value[i]
                    const userHotkey = userHotkeys[j]
                    if (hotkey && userHotkey && hotkey.alias === userHotkey.alias) {
                        hotkey.key = userHotkey.key
                        break
                    }
                }
            }
        } catch (error) {
            console.error('[Settings] Error in setUserHotkeys:', error)
            resetHotkeys()
        }
    }

    function resetHotkeys(): void {
        // we can't process .code, .keyCode property because they can be same up to 4 different .key values. Example: rR = KeyR,82  /? = Slash,191
        hotkeys.value = [
            // assess: new item navigation
            { key: 'ArrowUp', alias: HotkeyAction.COLLECTION_UP_1, icon: 'mdi-arrow-up' },
            { key: 'k', alias: HotkeyAction.COLLECTION_UP_2, icon: 'mdi-arrow-up' },
            { key: 'ArrowDown', alias: HotkeyAction.COLLECTION_DOWN_1, icon: 'mdi-arrow-down' },
            { key: 'j', alias: HotkeyAction.COLLECTION_DOWN_2, icon: 'mdi-arrow-down' },
            { key: 'Enter', alias: HotkeyAction.SHOW_ITEM_1, icon: 'mdi-text-box-outline' },
            { key: 'ArrowRight', alias: HotkeyAction.SHOW_ITEM_2, icon: 'mdi-text-box-outline' },
            { key: 'l', alias: HotkeyAction.SHOW_ITEM_3, icon: 'mdi-text-box-outline' },
            { key: 'Escape', alias: HotkeyAction.CLOSE_ITEM_1, icon: 'mdi-close-box-outline' },
            { key: 'ArrowLeft', alias: HotkeyAction.CLOSE_ITEM_2, icon: 'mdi-close-box-outline' },
            { key: 'h', alias: HotkeyAction.CLOSE_ITEM_3, icon: 'mdi-close-box-outline' },
            { key: 'Home', alias: HotkeyAction.HOME, icon: 'mdi-arrow-collapse-up' },
            { key: 'End', alias: HotkeyAction.END, icon: 'mdi-arrow-collapse-down' },
            // assess: OSINT source group navigation
            { key: 'K', alias: HotkeyAction.SOURCE_GROUP_UP, icon: 'mdi-arrow-up-circle-outline' },
            { key: 'J', alias: HotkeyAction.SOURCE_GROUP_DOWN, icon: 'mdi-arrow-down-circle-outline' },
            // assess: news item actions
            { key: 'r', alias: HotkeyAction.READ_ITEM, icon: 'mdi-eye-outline' },
            { key: 'i', alias: HotkeyAction.IMPORTANT_ITEM, icon: 'mdi-star-outline' },
            { key: 'u', alias: HotkeyAction.LIKE_ITEM, icon: 'mdi-thumb-up-outline' },
            { key: 'U', alias: HotkeyAction.UNLIKE_ITEM, icon: 'mdi-thumb-down-outline' },
            { key: 'Delete', alias: HotkeyAction.DELETE_ITEM, icon: 'mdi-delete-outline' },
            { key: 's', alias: HotkeyAction.SELECTION, icon: 'mdi-checkbox-multiple-marked-outline' },
            { key: 'g', alias: HotkeyAction.GROUP, icon: 'mdi-group' },
            { key: 'G', alias: HotkeyAction.UNGROUP, icon: 'mdi-ungroup' },
            { key: 'n', alias: HotkeyAction.NEW_PRODUCT, icon: 'mdi-file-outline' },
            { key: 'a', alias: HotkeyAction.AGGREGATE_OPEN, icon: 'mdi-newspaper-variant' },
            { key: 'o', alias: HotkeyAction.OPEN_ITEM_SOURCE, icon: 'mdi-open-in-app' },
            { key: '/', alias: HotkeyAction.OPEN_SEARCH, icon: 'mdi-card-search-outline' },
            { key: 'R', alias: HotkeyAction.RELOAD, icon: 'mdi-reload' },
            // switch views
            { key: 'v', alias: HotkeyAction.ENTER_VIEW_MODE, icon: 'mdi-view-headline' },
            { key: 'd', alias: HotkeyAction.DASHBOARD_VIEW, icon: 'mdi-view-dashboard-variant-outline' },
            { key: 'z', alias: HotkeyAction.ANALYZE_VIEW, icon: 'mdi-file-table' },
            { key: 'p', alias: HotkeyAction.PUBLISH_VIEW, icon: 'mdi mdi-send' },
            { key: 'c', alias: HotkeyAction.CONFIGURATION_VIEW, icon: 'mdi-cog' },
            // assess: filter actions
            { key: 'f', alias: HotkeyAction.ENTER_FILTER_MODE, icon: 'mdi-filter-outline' }
        ]
    }

    return {
        // State
        settings,
        spellcheck,
        hotkeys,
        word_lists,
        available_word_lists,

        // Getters
        getSettings,
        getProfileHotkeys,
        getProfileWordLists,
        getAvailableWordListsComputed,
        getProfileLanguage,
        getDateTimeFormat,

        // Actions
        getSetting,
        getSettingBoolean,
        loadSettings,
        saveSettings,
        loadUserWordLists,
        loadAvailableWordLists,
        saveUserWordLists,
        loadUserHotkeys,
        saveUserHotkeys,
        resetHotkeys
    }
})
