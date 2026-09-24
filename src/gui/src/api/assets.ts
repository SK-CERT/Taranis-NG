import ApiService from '@/services/api_service'
import type { Asset, AssetFilter, AssetGroup, NotificationTemplate } from '@/types/assets'

const query = (values: Record<string, string | number | boolean | undefined>): string => {
    const params = new URLSearchParams()
    Object.entries(values).forEach(([key, value]) => {
        if (value !== undefined && value !== '') params.set(key, String(value))
    })
    const encoded = params.toString()
    return encoded ? `?${encoded}` : ''
}

export const getAllAssetGroups = (filter: { search?: string } = {}) =>
    ApiService.get(`/my-assets/asset-groups${query({ search: filter.search })}`)

export const createNewAssetGroup = (group: Partial<AssetGroup>) => ApiService.post('/my-assets/asset-groups', group)
export const updateAssetGroup = (group: AssetGroup) => ApiService.put(`/my-assets/asset-groups/${group.id}`, group)
export const deleteAssetGroup = (group: Pick<AssetGroup, 'id'>) => ApiService.delete(`/my-assets/asset-groups/${group.id}`)

export const getAllNotificationTemplates = (filter: { search?: string } = {}) =>
    ApiService.get(`/my-assets/asset-notification-templates${query({ search: filter.search })}`)

export const createNewNotificationTemplate = (template: Partial<NotificationTemplate>) =>
    ApiService.post('/my-assets/asset-notification-templates', template)
export const updateNotificationTemplate = (template: NotificationTemplate) =>
    ApiService.put(`/my-assets/asset-notification-templates/${template.id}`, template)
export const deleteNotificationTemplate = (template: Pick<NotificationTemplate, 'id'>) =>
    ApiService.delete(`/my-assets/asset-notification-templates/${template.id}`)

export const getAllAssets = (data: { group_id: string; filter: AssetFilter }) =>
    ApiService.get(
        `/my-assets/asset-groups/${encodeURIComponent(data.group_id)}/assets${query({
            search: data.filter.search,
            sort: data.filter.sort,
            vulnerable: data.filter.vulnerable || undefined
        })}`
    )

export const createNewAsset = (asset: Partial<Asset> & { asset_group_id: string }) =>
    ApiService.post(`/my-assets/asset-groups/${encodeURIComponent(asset.asset_group_id)}/assets`, asset)
export const updateAsset = (asset: Asset) =>
    ApiService.put(`/my-assets/asset-groups/${encodeURIComponent(asset.asset_group_id)}/assets/${asset.id}`, asset)
export const deleteAsset = (asset: Pick<Asset, 'id' | 'asset_group_id'>) =>
    ApiService.delete(`/my-assets/asset-groups/${encodeURIComponent(asset.asset_group_id)}/assets/${asset.id}`)

export const solveVulnerability = (data: { group_id: string; asset_id: number; vulnerability_id: number; solved: boolean }) =>
    ApiService.put(
        `/my-assets/asset-groups/${encodeURIComponent(data.group_id)}/assets/${data.asset_id}/vulnerabilities/${data.vulnerability_id}`,
        { solved: data.solved }
    )

export const findAttributeCPE = () => ApiService.get('/my-assets/attributes/cpe')
export const getCPEAttributeEnums = (filter: { search?: string; offset?: number; limit?: number } = {}) =>
    ApiService.get(
        `/my-assets/attributes/cpe/enums${query({ search: filter.search, offset: filter.offset ?? 0, limit: filter.limit ?? 20 })}`
    )
