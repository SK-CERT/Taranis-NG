import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getAllACLEntries,
  getAllAttributes,
  getAllAiProviders,
  getAllDataProviders,
  getAllBotPresets,
  getAllBotsNodes,
  getAllCollectorsNodes,
  getAllExternalPermissions,
  getAllExternalUsers,
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
  getAllWordLists,
  getAllStateDefinitions,
  createNewStateDefinition,
  updateStateDefinition,
  deleteStateDefinition,
  getAllStateEntityTypes
} from '@/api/config'
import { getAllUserProductTypes } from '@/api/user'
import { getAllOSINTSourceGroupsAssess } from '@/api/assess'

export const useConfigStore = defineStore('config', () => {
  // State
  const attributes = ref({ total_count: 0, items: [] })
  const aiProviders = ref({ total_count: 0, items: [] })
  const dataProviders = ref({ total_count: 0, items: [] })
  const reportItemTypesConfig = ref({ total_count: 0, items: [] })
  const productTypes = ref({ total_count: 0, items: [] })
  const allPermissions = ref({ total_count: 0, items: [] })
  const roles = ref({ total_count: 0, items: [] })
  const acls = ref({ total_count: 0, items: [] })
  const organizations = ref({ total_count: 0, items: [] })
  const users = ref({ total_count: 0, items: [] })
  const wordLists = ref({ total_count: 0, items: [] })
  const remoteAccess = ref({ total_count: 0, items: [] })
  const remoteNodes = ref({ total_count: 0, items: [] })
  const collectorsNodes = ref({ total_count: 0, items: [] })
  const osintSources = ref({ total_count: 0, items: [] })
  const osintSourceGroups = ref({ total_count: 0, items: [] })
  const presentersNodes = ref({ total_count: 0, items: [] })
  const publishersNodes = ref({ total_count: 0, items: [] })
  const publisherPresets = ref({ total_count: 0, items: [] })
  const botsNodes = ref({ total_count: 0, items: [] })
  const botPresets = ref({ total_count: 0, items: [] })
  const stateDefinitions = ref({ total_count: 0, items: [] })
  const stateEntityTypes = ref({ total_count: 0, items: [] })

  // Getters
  const osintSourceGroupsForAssess = computed(() => {
    // Build groups list for Assess including "All" category
    const groups = []
    groups.push({
      icon: 'mdi-folder-multiple',
      color: '#81D4FA',
      title: 'osint_source_group.all',
      translate: '1',
      route: '/assess/group/all',
      id: 'all'
    })

    const items =
      osintSourceGroups.value && osintSourceGroups.value.items ? osintSourceGroups.value.items : []

    for (let i = 0; i < items.length; i++) {
      const g = items[i]
      let title = g.name
      let translate = ''
      let color = null
      if (g.default === true) {
        title = 'osint_source_group.default_group'
        translate = '1'
        color = '#BDBDBD'
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
  async function loadAttributes(data) {
    const response = await getAllAttributes(data)
    attributes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadAiProviders(data) {
    const response = await getAllAiProviders(data)
    aiProviders.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadDataProviders(data) {
    const response = await getAllDataProviders(data)
    dataProviders.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadReportItemTypesConfig(data) {
    const response = await getAllReportItemTypes(data)
    reportItemTypesConfig.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadProductTypes(data) {
    const response = await getAllProductTypes(data)
    productTypes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadUserProductTypes(data) {
    const response = await getAllUserProductTypes(data)
    productTypes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadPermissions(data) {
    const response = await getAllPermissions(data)
    allPermissions.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadExternalPermissions(data) {
    const response = await getAllExternalPermissions(data)
    allPermissions.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadRoles(data) {
    const response = await getAllRoles(data)
    roles.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadACLEntries(data) {
    const response = await getAllACLEntries(data)
    acls.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadOrganizations(data) {
    const response = await getAllOrganizations(data)
    organizations.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadUsers(data) {
    const response = await getAllUsers(data)
    users.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadExternalUsers(data) {
    const response = await getAllExternalUsers(data)
    users.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadWordLists(data) {
    const response = await getAllWordLists(data)
    wordLists.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadRemoteAccesses(data) {
    const response = await getAllRemoteAccesses(data)
    remoteAccess.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadRemoteNodes(data) {
    const response = await getAllRemoteNodes(data)
    remoteNodes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadCollectorsNodes(data) {
    const response = await getAllCollectorsNodes(data)
    collectorsNodes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadOSINTSources(data) {
    const response = await getAllOSINTSources(data)
    osintSources.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadOSINTSourceGroups(data) {
    const response = await getAllOSINTSourceGroups(data)
    osintSourceGroups.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadOSINTSourceGroupsAssess(data) {
    const response = await getAllOSINTSourceGroupsAssess(data)
    osintSourceGroups.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadPresentersNodes(data) {
    const response = await getAllPresentersNodes(data)
    presentersNodes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadPublishersNodes(data) {
    const response = await getAllPublishersNodes(data)
    publishersNodes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadPublisherPresets(data) {
    const response = await getAllPublisherPresets(data)
    publisherPresets.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadBotsNodes(data) {
    const response = await getAllBotsNodes(data)
    botsNodes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadBotPresets(data) {
    const response = await getAllBotPresets(data)
    botPresets.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadStateDefinitions(data) {
    const response = await getAllStateDefinitions(data)
    stateDefinitions.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function loadStateEntityTypes(data) {
    const response = await getAllStateEntityTypes(data)
    stateEntityTypes.value = response.data || { total_count: 0, items: [] }
    return response
  }

  async function createStateDefinition(data) {
    return await createNewStateDefinition(data)
  }

  async function modifyStateDefinition(data) {
    return await updateStateDefinition(data)
  }

  async function removeStateDefinition(data) {
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
    loadExternalUsers,
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
