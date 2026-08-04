import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAllAssetGroups, getAllAssets, getAllNotificationTemplates } from '@/api/assets'
import type { Asset, AssetFilter, AssetGroup, ListResponse, NotificationTemplate } from '@/types/assets'

type ApiResponse<T> = { data?: T }
const empty = <T>(): ListResponse<T> => ({ total_count: 0, items: [] })

export const useAssetsStore = defineStore('assets', () => {
    const assetGroups = ref<ListResponse<AssetGroup>>(empty())
    const notificationTemplates = ref<ListResponse<NotificationTemplate>>(empty())
    const assets = ref<ListResponse<Asset>>(empty())

    async function loadAssetGroups(filter: { search?: string } = {}): Promise<ApiResponse<ListResponse<AssetGroup>>> {
        const response = (await getAllAssetGroups(filter)) as ApiResponse<ListResponse<AssetGroup>>
        assetGroups.value = response.data || empty()
        return response
    }

    async function loadNotificationTemplates(filter: { search?: string } = {}): Promise<ApiResponse<ListResponse<NotificationTemplate>>> {
        const response = (await getAllNotificationTemplates(filter)) as ApiResponse<ListResponse<NotificationTemplate>>
        notificationTemplates.value = response.data || empty()
        return response
    }

    async function loadAssets(data: { group_id: string; filter: AssetFilter }): Promise<ApiResponse<ListResponse<Asset>>> {
        const response = (await getAllAssets(data)) as ApiResponse<ListResponse<Asset>>
        assets.value = response.data || empty()
        return response
    }

    function clearAssets(): void {
        assets.value = empty()
    }

    return { assetGroups, notificationTemplates, assets, loadAssetGroups, loadNotificationTemplates, loadAssets, clearAssets }
})
