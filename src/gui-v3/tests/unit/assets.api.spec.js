import { beforeEach, describe, expect, it, vi } from 'vitest'
import ApiService from '@/services/api_service'
import { createNewAsset, getAllAssets, solveVulnerability, updateAsset } from '@/api/assets'

vi.mock('@/services/api_service', () => ({
    default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

const asset = {
    id: 7,
    asset_group_id: 'group/a',
    name: 'Gateway',
    serial: 'GW-1',
    description: '',
    asset_cpes: [{ value: 'cpe:2.3:a:vendor:product:%' }]
}

describe('assets api', () => {
    beforeEach(() => vi.clearAllMocks())

    it('encodes group ids and filters when loading assets', () => {
        getAllAssets({ group_id: 'group/a', filter: { search: 'edge box', sort: 'VULNERABILITY', vulnerable: true } })
        expect(ApiService.get).toHaveBeenCalledWith(
            '/my-assets/asset-groups/group%2Fa/assets?search=edge+box&sort=VULNERABILITY&vulnerable=true'
        )
    })

    it('uses the group collection for creation', () => {
        createNewAsset(asset)
        expect(ApiService.post).toHaveBeenCalledWith('/my-assets/asset-groups/group%2Fa/assets', asset)
    })

    it('uses the asset resource for updates', () => {
        updateAsset(asset)
        expect(ApiService.put).toHaveBeenCalledWith('/my-assets/asset-groups/group%2Fa/assets/7', asset)
    })

    it('uses PUT and the report item id when toggling a vulnerability', () => {
        solveVulnerability({ group_id: 'group/a', asset_id: 7, vulnerability_id: 42, solved: true })
        expect(ApiService.put).toHaveBeenCalledWith('/my-assets/asset-groups/group%2Fa/assets/7/vulnerabilities/42', { solved: true })
    })
})
