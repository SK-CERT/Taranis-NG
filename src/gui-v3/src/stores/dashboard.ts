import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getDashboardData } from '@/api/dashboard'

type DashboardData = {
    total_news_items: number
    total_products: number
    total_report_items: number
    report_item_states: Record<string, unknown>
    product_states: Record<string, unknown>
    total_database_items: number
    latest_collected: string
    tag_cloud: unknown[]
    [key: string]: unknown
}

type ApiResponse<T> = {
    data?: T
}

const asNumber = (value: unknown): number => (typeof value === 'number' ? value : 0)
const asString = (value: unknown): string => (typeof value === 'string' ? value : '')
const asObject = (value: unknown): Record<string, unknown> => (value && typeof value === 'object' ? (value as Record<string, unknown>) : {})

const normalizeTagCloud = (value: unknown): unknown[] => {
    if (Array.isArray(value)) {
        return value
    }
    if (value && typeof value === 'object') {
        return Object.values(value)
    }
    return []
}

const toDashboardData = (value: unknown): DashboardData => {
    const source = asObject(value)
    return {
        total_news_items: asNumber(source['total_news_items']),
        total_products: asNumber(source['total_products']),
        total_report_items: asNumber(source['total_report_items']),
        report_item_states: asObject(source['report_item_states']),
        product_states: asObject(source['product_states']),
        total_database_items: asNumber(source['total_database_items']),
        latest_collected: asString(source['latest_collected']),
        tag_cloud: normalizeTagCloud(source['tag_cloud'])
    }
}

const emptyDashboardData = (): DashboardData => ({
    total_news_items: 0,
    total_products: 0,
    total_report_items: 0,
    report_item_states: {},
    product_states: {},
    total_database_items: 0,
    latest_collected: '',
    tag_cloud: []
})

export const useDashboardStore = defineStore('dashboard', () => {
    // State
    const dashboard_data = ref<DashboardData>(emptyDashboardData())

    // Getters
    const getDashboardDataComputed = computed(() => dashboard_data.value)

    // Actions
    async function loadDashboardData(): Promise<void> {
        try {
            const response = await getDashboardData()
            if (response && response.data) {
                dashboard_data.value = toDashboardData(response.data)
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
