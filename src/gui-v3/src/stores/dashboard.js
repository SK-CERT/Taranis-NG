import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDashboardData } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const dashboard_data = ref({
    total_news_items: 0,
    total_products: 0,
    total_report_items: 0,
    report_item_states: {},
    product_states: {},
    total_database_items: 0,
    latest_collected: '',
    tag_cloud: []
  })

  // Getters
  const getDashboardDataComputed = computed(() => dashboard_data.value)

  // Actions
  async function loadDashboardData() {
    try {
      const response = await getDashboardData()
      if (response && response.data) {
        const data = response.data

        // Ensure tag_cloud is always an array
        if (Array.isArray(data.tag_cloud)) {
          dashboard_data.value = data
        } else if (typeof data.tag_cloud === 'object' && data.tag_cloud !== null) {
          // Convert object to array if needed
          const tagCloudArray = Object.values(data.tag_cloud)
          dashboard_data.value = {
            ...data,
            tag_cloud: tagCloudArray
          }
        } else {
          // Fallback: ensure tag_cloud is array
          dashboard_data.value = {
            ...data,
            tag_cloud: Array.isArray(data.tag_cloud) ? data.tag_cloud : []
          }
        }

        console.log('[DashboardStore] Loaded dashboard data:', dashboard_data.value)
      } else {
        console.warn('[DashboardStore] No data received from API')
      }
    } catch (error) {
      console.error('[DashboardStore] Error loading dashboard data:', error)
      throw error
    }
  }

  return {
    // State
    dashboard_data,

    // Getters
    getDashboardDataComputed,

    // Actions
    loadDashboardData
  }
})
