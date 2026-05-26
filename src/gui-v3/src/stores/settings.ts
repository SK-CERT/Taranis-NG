import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getUserWordLists, getAvailableWordLists, updateUserWordLists, getHotkeys, updateHotkeys } from '@/api/user'
import { getAllSettings, updateSetting } from '@/api/config'
import Settings from '@/services/settings'
import type { SettingEntry } from '@/types/settings'

type HotkeyEntry = {
    key: string
    alias: string
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

    // Actions
    function getSetting(key: string): SettingEntry | null {
        try {
            const settingsArray = Array.isArray(settings.value) ? settings.value : []
            if (settingsArray.length === 0) return null
            if (typeof settingsArray.find !== 'function') {
                console.error('[Settings] settingsArray.find is not a function:', typeof settingsArray, settingsArray)
                return null
            }
            const setting = settingsArray.find((s) => s && s.key === key)
            return setting || null
        } catch (error) {
            console.error('[Settings] Error in getSetting:', key, error)
            return null
        }
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
            { key: 'ArrowUp', alias: 'collection_up_1', icon: 'mdi-arrow-up' },
            { key: 'k', alias: 'collection_up_2', icon: 'mdi-arrow-up' },
            { key: 'ArrowDown', alias: 'collection_down_1', icon: 'mdi-arrow-down' },
            { key: 'j', alias: 'collection_down_2', icon: 'mdi-arrow-down' },
            { key: 'Enter', alias: 'show_item_1', icon: 'mdi-text-box-outline' },
            { key: 'ArrowRight', alias: 'show_item_2', icon: 'mdi-text-box-outline' },
            { key: 'l', alias: 'show_item_3', icon: 'mdi-text-box-outline' },
            { key: 'Escape', alias: 'close_item_1', icon: 'mdi-close-box-outline' },
            { key: 'ArrowLeft', alias: 'close_item_2', icon: 'mdi-close-box-outline' },
            { key: 'h', alias: 'close_item_3', icon: 'mdi-close-box-outline' },
            { key: 'Home', alias: 'home', icon: 'mdi-arrow-collapse-up' },
            { key: 'End', alias: 'end', icon: 'mdi-arrow-collapse-down' },
            // assess: OSINT source group navigation
            { key: 'K', alias: 'source_group_up', icon: 'mdi-arrow-up-circle-outline' },
            { key: 'J', alias: 'source_group_down', icon: 'mdi-arrow-down-circle-outline' },
            // assess: news item actions
            { key: 'r', alias: 'read_item', icon: 'mdi-eye-outline' },
            { key: 'i', alias: 'important_item', icon: 'mdi-star-outline' },
            { key: 'u', alias: 'like_item', icon: 'mdi-thumb-up-outline' },
            { key: 'U', alias: 'unlike_item', icon: 'mdi-thumb-down-outline' },
            { key: 'Delete', alias: 'delete_item', icon: 'mdi-delete-outline' },
            { key: 's', alias: 'selection', icon: 'mdi-checkbox-multiple-marked-outline' },
            { key: 'g', alias: 'group', icon: 'mdi-group' },
            { key: 'G', alias: 'ungroup', icon: 'mdi-ungroup' },
            { key: 'n', alias: 'new_product', icon: 'mdi-file-outline' },
            { key: 'a', alias: 'aggregate_open', icon: 'mdi-newspaper-variant' },
            { key: 'o', alias: 'open_item_source', icon: 'mdi-open-in-app' },
            { key: '/', alias: 'open_search', icon: 'mdi-card-search-outline' },
            { key: 'R', alias: 'reload', icon: 'mdi-reload' },
            // switch views
            { key: 'v', alias: 'enter_view_mode', icon: 'mdi-view-headline' },
            { key: 'd', alias: 'dashboard_view', icon: 'mdi-view-dashboard-variant-outline' },
            { key: 'z', alias: 'analyze_view', icon: 'mdi-file-table' },
            { key: 'p', alias: 'publish_view', icon: 'mdi mdi-send' },
            { key: 'm', alias: 'my_assets_view', icon: 'mdi-file-cabinet' },
            { key: 'c', alias: 'configuration_view', icon: 'mdi-cog' },
            // assess: filter actions
            { key: 'f', alias: 'enter_filter_mode', icon: 'mdi-filter-outline' }
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

        // Actions
        getSetting,
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
