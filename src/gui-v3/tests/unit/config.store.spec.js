import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useConfigStore } from '@/stores/config'

// Mock all API modules used by the config store
vi.mock('@/api/config', () => ({
  getAllACLEntries: vi.fn(),
  getAllAttributes: vi.fn(),
  getAllAiProviders: vi.fn(),
  getAllDataProviders: vi.fn(),
  getAllBotPresets: vi.fn(),
  getAllBotsNodes: vi.fn(),
  getAllCollectorsNodes: vi.fn(),
  getAllExternalPermissions: vi.fn(),
  getAllExternalUsers: vi.fn(),
  getAllOrganizations: vi.fn(),
  getAllOSINTSourceGroups: vi.fn(),
  getAllOSINTSources: vi.fn(),
  getAllPermissions: vi.fn(),
  getAllPresentersNodes: vi.fn(),
  getAllProductTypes: vi.fn(),
  getAllPublisherPresets: vi.fn(),
  getAllPublishersNodes: vi.fn(),
  getAllRemoteAccesses: vi.fn(),
  getAllRemoteNodes: vi.fn(),
  getAllReportItemTypes: vi.fn(),
  getAllRoles: vi.fn(),
  getAllUsers: vi.fn(),
  getAllWordLists: vi.fn(),
  getAllStateDefinitions: vi.fn(),
  createNewStateDefinition: vi.fn(),
  updateStateDefinition: vi.fn(),
  deleteStateDefinition: vi.fn(),
  getAllStateEntityTypes: vi.fn()
}))

vi.mock('@/api/user', () => ({
  getAllUserProductTypes: vi.fn()
}))

vi.mock('@/api/assess', () => ({
  getAllOSINTSourceGroupsAssess: vi.fn()
}))

// Helper to create standard paginated response
function makeResponse(items, total_count = null) {
  return {
    data: {
      total_count: total_count ?? items.length,
      items
    }
  }
}

describe('Config Store', () => {
  let configApi
  let userApi
  let assessApi

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    configApi = await import('@/api/config')
    userApi = await import('@/api/user')
    assessApi = await import('@/api/assess')
  })

  // ── Initial State ─────────────────────────────
  describe('Initial State', () => {
    it('should have empty items for all entity types', () => {
      const store = useConfigStore()
      const entityRefs = [
        'attributes', 'aiProviders', 'dataProviders', 'reportItemTypesConfig',
        'productTypes', 'allPermissions', 'roles', 'acls', 'organizations',
        'users', 'wordLists', 'remoteAccess', 'remoteNodes', 'collectorsNodes',
        'osintSources', 'osintSourceGroups', 'presentersNodes', 'publishersNodes',
        'publisherPresets', 'botsNodes', 'botPresets', 'stateDefinitions', 'stateEntityTypes'
      ]

      for (const key of entityRefs) {
        expect(store[key]).toEqual({ total_count: 0, items: [] })
      }
    })
  })

  // ── Load Actions (representative sample) ──────
  // All load actions follow the same pattern; test a few representative ones
  describe('Load Actions', () => {
    const loadTests = [
      { action: 'loadRoles', stateKey: 'roles', apiFn: 'getAllRoles' },
      { action: 'loadOrganizations', stateKey: 'organizations', apiFn: 'getAllOrganizations' },
      { action: 'loadUsers', stateKey: 'users', apiFn: 'getAllUsers' },
      { action: 'loadAttributes', stateKey: 'attributes', apiFn: 'getAllAttributes' },
      { action: 'loadWordLists', stateKey: 'wordLists', apiFn: 'getAllWordLists' },
      { action: 'loadProductTypes', stateKey: 'productTypes', apiFn: 'getAllProductTypes' },
      { action: 'loadOSINTSources', stateKey: 'osintSources', apiFn: 'getAllOSINTSources' },
      { action: 'loadCollectorsNodes', stateKey: 'collectorsNodes', apiFn: 'getAllCollectorsNodes' },
      { action: 'loadACLEntries', stateKey: 'acls', apiFn: 'getAllACLEntries' },
      { action: 'loadStateDefinitions', stateKey: 'stateDefinitions', apiFn: 'getAllStateDefinitions' }
    ]

    it.each(loadTests)(
      '$action should fetch data and update $stateKey',
      async ({ action, stateKey, apiFn }) => {
        const mockItems = [{ id: 1, name: 'Test Item' }]
        vi.mocked(configApi[apiFn]).mockResolvedValue(makeResponse(mockItems))

        const store = useConfigStore()
        await store[action]()

        expect(configApi[apiFn]).toHaveBeenCalled()
        expect(store[stateKey].items).toEqual(mockItems)
        expect(store[stateKey].total_count).toBe(1)
      }
    )

    it.each(loadTests)(
      '$action should pass filter data to API call',
      async ({ action, apiFn }) => {
        vi.mocked(configApi[apiFn]).mockResolvedValue(makeResponse([]))

        const store = useConfigStore()
        const filterData = { search: 'test', offset: 0, limit: 20 }
        await store[action](filterData)

        expect(configApi[apiFn]).toHaveBeenCalledWith(filterData)
      }
    )

    it('should default to empty items when API returns null data', async () => {
      vi.mocked(configApi.getAllRoles).mockResolvedValue({ data: null })

      const store = useConfigStore()
      await store.loadRoles()

      expect(store.roles).toEqual({ total_count: 0, items: [] })
    })

    it('should return the API response from load actions', async () => {
      const response = makeResponse([{ id: 1 }])
      vi.mocked(configApi.getAllUsers).mockResolvedValue(response)

      const store = useConfigStore()
      const result = await store.loadUsers()

      expect(result).toBe(response)
    })
  })

  // ── External/Alternative Load Actions ─────────
  describe('Alternative Load Actions', () => {
    it('loadExternalPermissions should update allPermissions', async () => {
      const perms = [{ id: 'ext1', name: 'External Perm' }]
      vi.mocked(configApi.getAllExternalPermissions).mockResolvedValue(makeResponse(perms))

      const store = useConfigStore()
      await store.loadExternalPermissions()

      expect(store.allPermissions.items).toEqual(perms)
    })

    it('loadExternalUsers should update users', async () => {
      const extUsers = [{ id: 'ext-u1', name: 'External User' }]
      vi.mocked(configApi.getAllExternalUsers).mockResolvedValue(makeResponse(extUsers))

      const store = useConfigStore()
      await store.loadExternalUsers()

      expect(store.users.items).toEqual(extUsers)
    })

    it('loadUserProductTypes should update productTypes from user API', async () => {
      const types = [{ id: 1, title: 'Product A' }]
      vi.mocked(userApi.getAllUserProductTypes).mockResolvedValue(makeResponse(types))

      const store = useConfigStore()
      await store.loadUserProductTypes()

      expect(store.productTypes.items).toEqual(types)
    })

    it('loadOSINTSourceGroupsAssess should update osintSourceGroups from assess API', async () => {
      const groups = [{ id: 1, name: 'Assess Group' }]
      vi.mocked(assessApi.getAllOSINTSourceGroupsAssess).mockResolvedValue(makeResponse(groups))

      const store = useConfigStore()
      await store.loadOSINTSourceGroupsAssess()

      expect(store.osintSourceGroups.items).toEqual(groups)
    })
  })

  // ── State Definition CRUD ─────────────────────
  describe('State Definition CRUD', () => {
    it('createStateDefinition should call createNewStateDefinition', async () => {
      const newDef = { name: 'New State', entity_type: 'report_item' }
      const response = { data: { id: 1, ...newDef } }
      vi.mocked(configApi.createNewStateDefinition).mockResolvedValue(response)

      const store = useConfigStore()
      const result = await store.createStateDefinition(newDef)

      expect(configApi.createNewStateDefinition).toHaveBeenCalledWith(newDef)
      expect(result).toBe(response)
    })

    it('modifyStateDefinition should call updateStateDefinition', async () => {
      const updated = { id: 1, name: 'Updated State' }
      const response = { data: updated }
      vi.mocked(configApi.updateStateDefinition).mockResolvedValue(response)

      const store = useConfigStore()
      const result = await store.modifyStateDefinition(updated)

      expect(configApi.updateStateDefinition).toHaveBeenCalledWith(updated)
      expect(result).toBe(response)
    })

    it('removeStateDefinition should call deleteStateDefinition', async () => {
      const response = { data: { message: 'deleted' } }
      vi.mocked(configApi.deleteStateDefinition).mockResolvedValue(response)

      const store = useConfigStore()
      const result = await store.removeStateDefinition({ id: 1 })

      expect(configApi.deleteStateDefinition).toHaveBeenCalledWith({ id: 1 })
      expect(result).toBe(response)
    })
  })

  // ── osintSourceGroupsForAssess Getter ─────────
  describe('osintSourceGroupsForAssess getter', () => {
    it('should always include "All" group as first item', () => {
      const store = useConfigStore()
      const groups = store.osintSourceGroupsForAssess

      expect(groups[0]).toMatchObject({
        id: 'all',
        title: 'osint_source_group.all',
        route: '/assess/group/all'
      })
    })

    it('should include loaded groups after "All"', async () => {
      vi.mocked(configApi.getAllOSINTSourceGroups).mockResolvedValue(
        makeResponse([
          { id: 10, name: 'Group A', default: false },
          { id: 20, name: 'Group B', default: false }
        ])
      )

      const store = useConfigStore()
      await store.loadOSINTSourceGroups()

      const groups = store.osintSourceGroupsForAssess
      expect(groups).toHaveLength(3) // All + 2 groups
      expect(groups[1]).toMatchObject({ id: 10, title: 'Group A', route: '/assess/group/10' })
      expect(groups[2]).toMatchObject({ id: 20, title: 'Group B', route: '/assess/group/20' })
    })

    it('should use translated title for default groups', async () => {
      vi.mocked(configApi.getAllOSINTSourceGroups).mockResolvedValue(
        makeResponse([{ id: 5, name: 'Default', default: true }])
      )

      const store = useConfigStore()
      await store.loadOSINTSourceGroups()

      const groups = store.osintSourceGroupsForAssess
      expect(groups[1]).toMatchObject({
        title: 'osint_source_group.default_group',
        translate: '1',
        color: '#BDBDBD'
      })
    })

    it('should return only "All" when osintSourceGroups is empty', () => {
      const store = useConfigStore()
      expect(store.osintSourceGroupsForAssess).toHaveLength(1)
    })
  })

  // ── Error Handling ────────────────────────────
  describe('Error Handling', () => {
    it('should propagate API errors from load actions', async () => {
      vi.mocked(configApi.getAllRoles).mockRejectedValue(new Error('Network error'))

      const store = useConfigStore()
      await expect(store.loadRoles()).rejects.toThrow('Network error')

      // State should remain at default
      expect(store.roles).toEqual({ total_count: 0, items: [] })
    })

    it('should propagate errors from CRUD actions', async () => {
      vi.mocked(configApi.createNewStateDefinition).mockRejectedValue(new Error('403'))

      const store = useConfigStore()
      await expect(store.createStateDefinition({})).rejects.toThrow('403')
    })
  })
})
