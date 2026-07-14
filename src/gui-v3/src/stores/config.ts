import { defineStore } from 'pinia'
import { computed, ref, type Ref } from 'vue'
import {
    getAllACLEntries,
    getAllAttributes,
    getAllAiProviders,
    getAllDataProviders,
    getAllBotPresets,
    getAllBotsNodes,
    getAllCollectorsNodes,
    getAllExternalPermissions,
    getAllOrganizations,
    getAllOSINTSourceGroups,
    getAllOSINTSources,
    getAllPermissions,
    getAllPresentersNodes,
    getAllProductTypes,
    getAllPublisherPresets,
    getAllPublishersNodes,
    getAllRemoteAccesses,
    getAllRemoteNodes,
    getAllReportItemTypes,
    getAllRoles,
    getAllUsers,
    getAllAuthProviders,
    getAllWordLists,
    getAllStateDefinitions,
    createNewStateDefinition,
    updateStateDefinition,
    deleteStateDefinition,
    getAllStateEntityTypes
} from '@/api/config'
import { getAllUserProductTypes } from '@/api/user'
import { getAllOSINTSourceGroupsAssess } from '@/api/assess'

type FilterPayload = Record<string, unknown>

type ListState<T = unknown> = {
    total_count: number
    items: T[]
}

type ApiResponse<T> = {
    data?: T
}

type OSINTGroupItem = {
    id: string | number
    name?: string
    default?: boolean
}

type AssessOSINTGroup = {
    icon: string
    color: string | null
    title: string
    translate: boolean | null
    route: string
    id: string | number
}

const emptyListState = <T = unknown>(): ListState<T> => ({ total_count: 0, items: [] })

async function loadListState<T = unknown>(
    fetcher: (data: FilterPayload) => Promise<ApiResponse<ListState<T>>>,
    data: FilterPayload,
    target: Ref<ListState<T>>
): Promise<ApiResponse<ListState<T>>> {
    const response = await fetcher(data)
    target.value = response.data || emptyListState<T>()
    return response
}

export const useConfigStore = defineStore('config', () => {
    // State
    const attributes = ref<ListState>(emptyListState())
    const aiProviders = ref<ListState>(emptyListState())
    const dataProviders = ref<ListState>(emptyListState())
    const reportItemTypesConfig = ref<ListState>(emptyListState())
    const productTypes = ref<ListState>(emptyListState())
    const allPermissions = ref<ListState>(emptyListState())
    const roles = ref<ListState>(emptyListState())
    const acls = ref<ListState>(emptyListState())
    const organizations = ref<ListState>(emptyListState())
    const users = ref<ListState>(emptyListState())
    const authProviders = ref<ListState>(emptyListState())
    const wordLists = ref<ListState>(emptyListState())
    const remoteAccess = ref<ListState>(emptyListState())
    const remoteNodes = ref<ListState>(emptyListState())
    const collectorsNodes = ref<ListState>(emptyListState())
    const osintSources = ref<ListState>(emptyListState())
    const osintSourceGroups = ref<ListState<OSINTGroupItem>>(emptyListState())
    const presentersNodes = ref<ListState>(emptyListState())
    const publishersNodes = ref<ListState>(emptyListState())
    const publisherPresets = ref<ListState>(emptyListState())
    const botsNodes = ref<ListState>(emptyListState())
    const botPresets = ref<ListState>(emptyListState())
    const stateDefinitions = ref<ListState>(emptyListState())
    const stateEntityTypes = ref<ListState>(emptyListState())

    // Getters
    const osintSourceGroupsForAssess = computed<AssessOSINTGroup[]>(() => {
        // Build groups list for Assess including "All" category.
        const groups: AssessOSINTGroup[] = []
        groups.push({
            icon: 'mdi-folder-multiple',
            color: null,
            title: 'collectors.groups.all',
            translate: true,
            route: '/assess/group/all',
            id: 'all'
        })

        const items = osintSourceGroups.value && osintSourceGroups.value.items ? osintSourceGroups.value.items : []

        for (const g of items) {
            if (!g) {
                continue
            }
            let title = g.name || ''
            let translate = false
            const color: string | null = null
            if (g.default === true) {
                title = 'collectors.groups.default_group'
                translate = true
            }
            groups.push({
                icon: 'mdi-folder-multiple',
                color: color,
                title: title,
                translate: translate,
                route: '/assess/group/' + g.id,
                id: g.id
            })
        }
        return groups
    })

    // Actions
    async function loadAttributes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllAttributes, data, attributes)
    }

    async function loadAiProviders(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllAiProviders, data, aiProviders)
    }

    async function loadDataProviders(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllDataProviders, data, dataProviders)
    }

    async function loadReportItemTypesConfig(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllReportItemTypes, data, reportItemTypesConfig)
    }

    async function loadProductTypes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllProductTypes, data, productTypes)
    }

    async function loadUserProductTypes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllUserProductTypes, data, productTypes)
    }

    async function loadPermissions(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllPermissions, data, allPermissions)
    }

    async function loadExternalPermissions(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllExternalPermissions, data, allPermissions)
    }

    async function loadRoles(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllRoles, data, roles)
    }

    async function loadACLEntries(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllACLEntries, data, acls)
    }

    async function loadOrganizations(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllOrganizations, data, organizations)
    }

    async function loadUsers(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllUsers, data, users)
    }

    async function loadAuthProviders(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllAuthProviders, data, authProviders)
    }

    async function loadWordLists(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllWordLists, data, wordLists)
    }

    async function loadRemoteAccesses(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllRemoteAccesses, data, remoteAccess)
    }

    async function loadRemoteNodes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllRemoteNodes, data, remoteNodes)
    }

    async function loadCollectorsNodes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllCollectorsNodes, data, collectorsNodes)
    }

    async function loadOSINTSources(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllOSINTSources, data, osintSources)
    }

    async function loadOSINTSourceGroups(data: FilterPayload): Promise<ApiResponse<ListState<OSINTGroupItem>>> {
        return await loadListState(getAllOSINTSourceGroups, data, osintSourceGroups)
    }

    async function loadOSINTSourceGroupsAssess(data: FilterPayload): Promise<ApiResponse<ListState<OSINTGroupItem>>> {
        return await loadListState(getAllOSINTSourceGroupsAssess, data, osintSourceGroups)
    }

    async function loadPresentersNodes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllPresentersNodes, data, presentersNodes)
    }

    async function loadPublishersNodes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllPublishersNodes, data, publishersNodes)
    }

    async function loadPublisherPresets(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllPublisherPresets, data, publisherPresets)
    }

    async function loadBotsNodes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllBotsNodes, data, botsNodes)
    }

    async function loadBotPresets(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllBotPresets, data, botPresets)
    }

    async function loadStateDefinitions(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllStateDefinitions, data, stateDefinitions)
    }

    async function loadStateEntityTypes(data: FilterPayload): Promise<ApiResponse<ListState>> {
        return await loadListState(getAllStateEntityTypes, data, stateEntityTypes)
    }

    async function createStateDefinition(data: Record<string, unknown>): Promise<unknown> {
        return await createNewStateDefinition(data)
    }

    async function modifyStateDefinition(data: Record<string, unknown>): Promise<unknown> {
        return await updateStateDefinition(data)
    }

    async function removeStateDefinition(data: Record<string, unknown>): Promise<unknown> {
        return await deleteStateDefinition(data)
    }

    return {
        // State
        attributes,
        aiProviders,
        dataProviders,
        reportItemTypesConfig,
        productTypes,
        allPermissions,
        roles,
        acls,
        organizations,
        users,
        authProviders,
        wordLists,
        remoteAccess,
        remoteNodes,
        collectorsNodes,
        osintSources,
        osintSourceGroups,
        presentersNodes,
        publishersNodes,
        publisherPresets,
        botsNodes,
        botPresets,
        stateDefinitions,
        stateEntityTypes,

        // Getters
        osintSourceGroupsForAssess,

        // Actions
        loadAttributes,
        loadAiProviders,
        loadDataProviders,
        loadReportItemTypesConfig,
        loadProductTypes,
        loadUserProductTypes,
        loadPermissions,
        loadExternalPermissions,
        loadRoles,
        loadACLEntries,
        loadOrganizations,
        loadUsers,
        loadAuthProviders,
        loadWordLists,
        loadRemoteAccesses,
        loadRemoteNodes,
        loadCollectorsNodes,
        loadOSINTSources,
        loadOSINTSourceGroups,
        loadOSINTSourceGroupsAssess,
        loadPresentersNodes,
        loadPublishersNodes,
        loadPublisherPresets,
        loadBotsNodes,
        loadBotPresets,
        loadStateDefinitions,
        loadStateEntityTypes,
        createStateDefinition,
        modifyStateDefinition,
        removeStateDefinition
    }
})
