import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getAllAssetGroups, getAllAssets, getAllNotificationTemplates } from '@/api/assets'

export const useAssetsStore = defineStore('assets', () => {
  // State
  const asset_groups = ref({ total_count: 0, items: [] })
  const notification_templates = ref({ total_count: 0, items: [] })
  const assets = ref({ total_count: 0, items: [] })

  // Getters
  const getAssetGroups = computed(() => asset_groups.value)
  const getAssets = computed(() => assets.value)
  const getNotificationTemplates = computed(() => notification_templates.value)

  // Actions
  async function loadAssetGroups(data) {
    const response = await getAllAssetGroups(data)
    asset_groups.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadAssets(data) {
    const response = await getAllAssets(data)
    assets.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadNotificationTemplates(data) {
    const response = await getAllNotificationTemplates(data)
    notification_templates.value = response.data || { total_count: 0, items: [] }
    return response
  }

  return {
    // State
    asset_groups,
    notification_templates,
    assets,

    // Getters
    getAssetGroups,
    getAssets,
    getNotificationTemplates,

    // Actions
    loadAssetGroups,
    loadAssets,
    loadNotificationTemplates
  }
})
