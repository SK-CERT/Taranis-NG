import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAllAssetGroups, getAllAssets, getAllNotificationTemplates } from '@/api/assets'

type LoadPayload = Record<string, unknown>

type TotalItemsState = {
    total_count: number
    items: unknown[]
}

type ApiResponse<T> = {
    data?: T
}

const emptyListState = (): TotalItemsState => ({ total_count: 0, items: [] })

export const useAssetsStore = defineStore('assets', () => {
    // State
    const asset_groups = ref<TotalItemsState>(emptyListState())
    const notification_templates = ref<TotalItemsState>(emptyListState())
    const assets = ref<TotalItemsState>(emptyListState())

    // Getters
    const getAssetGroups = computed(() => asset_groups.value)
    const getAssets = computed(() => assets.value)
    const getNotificationTemplates = computed(() => notification_templates.value)

    // Actions
    async function loadAssetGroups(data: LoadPayload): Promise<ApiResponse<unknown>> {
        const response = (await getAllAssetGroups(data)) as ApiResponse<TotalItemsState>
        asset_groups.value = response.data || emptyListState()
        return response
    }

    async function loadAssets(data: LoadPayload): Promise<ApiResponse<unknown>> {
        const response = (await getAllAssets(data)) as ApiResponse<TotalItemsState>
        assets.value = response.data || emptyListState()
        return response
    }

    async function loadNotificationTemplates(data: LoadPayload): Promise<ApiResponse<unknown>> {
        const response = (await getAllNotificationTemplates(data)) as ApiResponse<TotalItemsState>
        notification_templates.value = response.data || emptyListState()
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
