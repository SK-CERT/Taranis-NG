import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getUserWordLists,
  getAvailableWordLists,
  updateUserWordLists,
  getHotkeys,
  updateHotkeys
} from '@/api/user'
import { getAllSettings, updateSetting } from '@/api/config'
import Settings from '@/services/settings'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref([])
  const spellcheck = ref(true)
  const hotkeys = ref([])
  const word_lists = ref([])
  const available_word_lists = ref([])

  // Getters
  const getSettings = computed(() => (Array.isArray(settings.value) ? settings.value : []))

  const getProfileHotkeys = computed(() => (Array.isArray(hotkeys.value) ? hotkeys.value : []))

  const getProfileWordLists = computed(() =>
    Array.isArray(word_lists.value) ? word_lists.value : []
  )

  const getAvailableWordListsComputed = computed(() =>
    Array.isArray(available_word_lists.value) ? available_word_lists.value : []
  )

  const getProfileLanguage = computed(() => {
    // Use internal getSetting to avoid circular dependency
    const settingsArray = Array.isArray(settings.value) ? settings.value : []
    const uiLangSetting = settingsArray.find((item) => item.key === Settings.UI_LANGUAGE)
    let lng = uiLangSetting ? uiLangSetting.value : null

    if (!lng) {
      lng = navigator.language.split('-')[0]
    }
    if (!lng && typeof import.meta.env.VITE_APP_TARANIS_NG_LOCALE !== 'undefined') {
      lng = import.meta.env.VITE_APP_TARANIS_NG_LOCALE
    }
    if (!lng) {
      lng = 'en'
    }
    return lng
  })

  // Actions
  function getSetting(key) {
    try {
      const settingsArray = Array.isArray(settings.value) ? settings.value : []
      if (settingsArray.length === 0) return null
      if (typeof settingsArray.find !== 'function') {
        console.error(
          '[Settings] settingsArray.find is not a function:',
          typeof settingsArray,
          settingsArray
        )
        return null
      }
      const setting = settingsArray.find((s) => s && s.key === key)
      return setting || null
    } catch (error) {
      console.error('[Settings] Error in getSetting:', key, error)
      return null
    }
  }

  async function loadSettings(data) {
    try {
      const response = await getAllSettings(data)
      // Ensure we always set an array
      const responseData = response?.data

      console.log(
        '[Settings] loadSettings response:',
        typeof responseData,
        Array.isArray(responseData),
        responseData
      )

      if (Array.isArray(responseData)) {
        settings.value = responseData
      } else if (
        responseData &&
        typeof responseData === 'object' &&
        Array.isArray(responseData.items)
      ) {
        settings.value = responseData.items
      } else {
        console.warn('[Settings] Unexpected response format, setting to empty array')
        settings.value = []
      }

      console.log(
        '[Settings] settings.value after load:',
        Array.isArray(settings.value),
        settings.value?.length
      )
      return response
    } catch (error) {
      console.error('[Settings] Error loading settings:', error)
      settings.value = []
      throw error
    }
  }

  async function saveSettings({ data, is_global }) {
    const response = await updateSetting(data, is_global)
    // Ensure we always set an array
    const responseData = response?.data
    if (Array.isArray(responseData)) {
      settings.value = responseData
    } else if (responseData && Array.isArray(responseData.items)) {
      settings.value = responseData.items
    } else {
      settings.value = []
    }
    return response
  }

  async function loadUserWordLists() {
    try {
      const response = await getUserWordLists()
      const responseData = response?.data

      console.log(
        '[Settings] loadUserWordLists response:',
        typeof responseData,
        Array.isArray(responseData),
        responseData
      )

      word_lists.value = Array.isArray(responseData) ? responseData : []

      console.log(
        '[Settings] word_lists.value after load:',
        Array.isArray(word_lists.value),
        word_lists.value?.length
      )
      return response
    } catch (error) {
      console.error('[Settings] Error loading word lists:', error)
      word_lists.value = []
      throw error
    }
  }

  async function loadAvailableWordLists(data) {
    try {
      const response = await getAvailableWordLists(data)
      const responseData = response?.data

      console.log('[Settings] loadAvailableWordLists response:', typeof responseData, responseData)

      if (responseData && Array.isArray(responseData.items)) {
        available_word_lists.value = responseData.items
      } else if (Array.isArray(responseData)) {
        available_word_lists.value = responseData
      } else {
        available_word_lists.value = []
      }

      console.log(
        '[Settings] available_word_lists.value after load:',
        Array.isArray(available_word_lists.value)
      )
      return response
    } catch (error) {
      console.error('[Settings] Error loading available word lists:', error)
      available_word_lists.value = []
      throw error
    }
  }

  async function saveUserWordLists(data) {
    try {
      const response = await updateUserWordLists(data)
      const responseData = response?.data
      word_lists.value = Array.isArray(responseData) ? responseData : []
      return response
    } catch (error) {
      console.error('[Settings] Error saving word lists:', error)
      throw error
    }
  }

  async function loadUserHotkeys() {
    try {
      const response = await getHotkeys()
      const responseData = response?.data

      console.log(
        '[Settings] loadUserHotkeys response:',
        typeof responseData,
        Array.isArray(responseData),
        responseData
      )

      setUserHotkeys(Array.isArray(responseData) ? responseData : [])

      console.log(
        '[Settings] hotkeys.value after load:',
        Array.isArray(hotkeys.value),
        hotkeys.value?.length
      )
      return response
    } catch (error) {
      console.error('[Settings] Error loading hotkeys:', error)
      setUserHotkeys([])
      throw error
    }
  }

  async function saveUserHotkeys(data) {
    try {
      const response = await updateHotkeys(data)
      const responseData = response?.data
      setUserHotkeys(Array.isArray(responseData) ? responseData : [])
      return response
    } catch (error) {
      console.error('[Settings] Error saving hotkeys:', error)
      throw error
    }
  }

  function setUserHotkeys(userHotkeys) {
    try {
      resetHotkeys()

      console.log(
        '[Settings] setUserHotkeys input:',
        typeof userHotkeys,
        Array.isArray(userHotkeys),
        userHotkeys
      )
      console.log(
        '[Settings] hotkeys.value after reset:',
        Array.isArray(hotkeys.value),
        hotkeys.value?.length
      )

      if (!Array.isArray(userHotkeys)) {
        console.warn('[Settings] userHotkeys is not an array:', typeof userHotkeys)
        return
      }

      if (!Array.isArray(hotkeys.value)) {
        console.error(
          '[Settings] hotkeys.value is not an array after reset!:',
          typeof hotkeys.value
        )
        resetHotkeys()
      }

      for (let i = 0; i < hotkeys.value.length; i++) {
        for (let j = 0; j < userHotkeys.length; j++) {
          if (hotkeys.value[i].alias === userHotkeys[j].alias) {
            hotkeys.value[i].key = userHotkeys[j].key
            break
          }
        }
      }

      console.log(
        '[Settings] setUserHotkeys completed, hotkeys.value:',
        Array.isArray(hotkeys.value),
        hotkeys.value?.length
      )
    } catch (error) {
      console.error('[Settings] Error in setUserHotkeys:', error)
      resetHotkeys()
    }
  }

  function resetHotkeys() {
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
