import {
  getAllACLEntries,
  getAllAttributes,
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
  getAllNodes,
  getAllWordLists
} from '@/api/config'
import { getAllUserProductTypes, getAllUserWordLists } from '@/api/user'

const state = {
  attributes: { total_count: 0, items: [] },
  report_item_types_config: { total_count: 0, items: [] },
  product_types: { total_count: 0, items: [] },
  all_permissions: { total_count: 0, items: [] },
  roles: { total_count: 0, items: [] },
  acls: { total_count: 0, items: [] },
  organizations: { total_count: 0, items: [] },
  users: { total_count: 0, items: [] },
  word_lists: { total_count: 0, items: [] },
  remote_access: { total_count: 0, items: [] },
  remote_nodes: { total_count: 0, items: [] },
  nodes: { total_count: 0, items: [] },
  osint_sources: { total_count: 0, items: [] },
  osint_source_groups: { total_count: 0, items: [] },
  presenters_nodes: { total_count: 0, items: [] },
  publishers_nodes: { total_count: 0, items: [] },
  publisher_presets: { total_count: 0, items: [] },
  bots_nodes: { total_count: 0, items: [] },
  bot_presets: { total_count: 0, items: [] }
}

const actions = {

  getAllAttributes (context, data) {
    return getAllAttributes(data)
      .then(response => {
        context.commit('setAttributes', response.data)
      })
  },

  loadReportItemTypesConfig (context, data) {
    return getAllReportItemTypes(data)
      .then(response => {
        context.commit('setReportItemTypesConfig', response.data)
      })
  },

  loadProductTypes (context, data) {
    return getAllProductTypes(data)
      .then(response => {
        context.commit('setProductTypes', response.data)
      })
  },

  loadUserProductTypes (context, data) {
    return getAllUserProductTypes(data)
      .then(response => {
        context.commit('setProductTypes', response.data)
      })
  },

  getAllPermissions (context, data) {
    return getAllPermissions(data)
      .then(response => {
        context.commit('setPermissions', response.data)
      })
  },

  getAllExternalPermissions (context, data) {
    return getAllExternalPermissions(data)
      .then(response => {
        context.commit('setPermissions', response.data)
      })
  },

  loadRoles (context, data) {
    return getAllRoles(data)
      .then(response => {
        context.commit('setRoles', response.data)
      })
  },

  loadACLEntries (context, data) {
    return getAllACLEntries(data)
      .then(response => {
        context.commit('setACLEntries', response.data)
      })
  },

  getAllOrganizations (context, data) {
    return getAllOrganizations(data)
      .then(response => {
        context.commit('setOrganizations', response.data)
      })
  },

  loadUsers (context, data) {
    return getAllUsers(data)
      .then(response => {
        context.commit('setUsers', response.data)
      })
  },

  getAllExternalUsers (context, data) {
    return getAllExternalUsers(data)
      .then(response => {
        context.commit('setUsers', response.data)
      })
  },

  loadWordLists (context, data) {
    return getAllWordLists(data)
      .then(response => {
        context.commit('setWordLists', response.data)
      })
  },

  getAllUserWordLists (context, data) {
    return getAllUserWordLists(data)
      .then(response => {
        context.commit('setWordLists', response.data)
      })
  },

  getAllRemoteAccesses (context, data) {
    return getAllRemoteAccesses(data)
      .then(response => {
        context.commit('setRemoteAccesses', response.data)
      })
  },

  getAllRemoteNodes (context, data) {
    return getAllRemoteNodes(data)
      .then(response => {
        context.commit('setRemoteNodes', response.data)
      })
  },

  loadCollectorsNodes (context, data) {
    return getAllCollectorsNodes(data)
      .then(response => {
        context.commit('setCollectorsNodes', response.data)
      })
  },

  loadNodes (context, data) {
    return getAllNodes(data)
      .then(response => {
        context.commit('setNodes', response.data)
      })
  },

  loadOSINTSources (context, data) {
    return getAllOSINTSources(data)
      .then(response => {
        context.commit('setOSINTSources', response.data)
      })
  },

  loadOSINTSourceGroups (context, filter) {
    return getAllOSINTSourceGroups(filter)
      .then(response => {
        context.commit('setOSINTSourceGroups', response.data)
      })
  },

  loadPresentersNodes (context, data) {
    return getAllPresentersNodes(data)
      .then(response => {
        context.commit('setPresentersNodes', response.data)
      })
  },

  getAllPublishersNodes (context, data) {
    return getAllPublishersNodes(data)
      .then(response => {
        context.commit('setPublishersNodes', response.data)
      })
  },

  getAllPublisherPresets (context, data) {
    return getAllPublisherPresets(data)
      .then(response => {
        context.commit('setPublisherPresets', response.data)
      })
  },

  getAllBotsNodes (context, data) {
    return getAllBotsNodes(data)
      .then(response => {
        context.commit('setBotsNodes', response.data)
      })
  },

  getAllBotPresets (context, data) {
    return getAllBotPresets(data)
      .then(response => {
        context.commit('setBotPresets', response.data)
      })
  }
}

const mutations = {
  setAttributes (state, new_attributes) {
    state.attributes = new_attributes
  },

  setReportItemTypesConfig (state, new_report_item_types_config) {
    state.report_item_types_config = new_report_item_types_config
  },

  setProductTypes (state, new_product_types) {
    state.product_types = new_product_types
  },

  setPermissions (state, new_permissions) {
    state.all_permissions = new_permissions
  },

  setRoles (state, new_roles) {
    state.roles = new_roles
  },

  setACLEntries (state, new_acls) {
    state.acls = new_acls
  },

  setOrganizations (state, new_organizations) {
    state.organizations = new_organizations
  },

  setUsers (state, new_users) {
    state.users = new_users
  },

  setWordLists (state, new_word_lists) {
    state.word_lists = new_word_lists
  },

  setRemoteAccesses (state, new_remote_access) {
    state.remote_access = new_remote_access
  },

  setRemoteNodes (state, new_remote_nodes) {
    state.remote_nodes = new_remote_nodes
  },

  setNodes (state, new_nodes) {
    state.nodes = new_nodes
  },

  setCollectorsNodes (state, new_collectors_nodes) {
    state.collectors_nodes = new_collectors_nodes
  },

  setOSINTSources (state, new_osint_sources) {
    state.osint_sources = new_osint_sources
  },

  setOSINTSourceGroups (state, new_osint_source_groups) {
    state.osint_source_groups = new_osint_source_groups
  },

  setPresentersNodes (state, new_presenters_nodes) {
    state.presenters_nodes = new_presenters_nodes
  },

  setPublishersNodes (state, new_publishers_nodes) {
    state.publishers_nodes = new_publishers_nodes
  },

  setPublisherPresets (state, new_publisher_presets) {
    state.publisher_presets = new_publisher_presets
  },

  setBotsNodes (state, new_bots_nodes) {
    state.bots_nodes = new_bots_nodes
  },

  setBotPresets (state, new_bot_presets) {
    state.bot_presets = new_bot_presets
  }
}

const getters = {
  getAttributes (state) {
    return state.attributes
  },

  getReportItemTypesConfig (state) {
    return state.report_item_types_config
  },

  getProductTypes (state) {
    return state.product_types
  },

  getAllPermissions (state) {
    return state.all_permissions
  },

  getRoles (state) {
    return state.roles
  },

  getACLEntries (state) {
    return state.acls
  },

  getOrganizations (state) {
    return state.organizations
  },

  getUsers (state) {
    return state.users
  },

  getWordLists (state) {
    return state.word_lists
  },

  getRemoteAccesses (state) {
    return state.remote_access
  },

  getRemoteNodes (state) {
    return state.remote_nodes
  },

  getCollectorsNodes (state) {
    state.collectors_nodes.items.map(function (item) {
      item.type = 'Collector'
      return item
    })
    return state.collectors_nodes
  },

  getNodes (state) {
    return state.nodes
  },

  getOSINTSources (state) {
    return state.osint_sources.items
  },

  getOSINTSourceGroups (state) {
    return state.osint_source_groups.items
  },

  getPresentersNodes (state) {
    state.presenters_nodes.items.map(function (item) {
      item.type = 'Presenter'
      return item
    })
    return state.presenters_nodes
  },

  getPublishersNodes (state) {
    state.publishers_nodes.items.map(function (item) {
      item.type = 'Publisher'
      return item
    })
    return state.publishers_nodes
  },

  getPublisherPresets (state) {
    return state.publisher_presets
  },

  getBotsNodes (state) {
    state.bots_nodes.items.map(function (item) {
      item.type = 'Bot'
      return item
    })
    return state.bots_nodes
  },

  getBotPresets (state) {
    return state.bot_presets
  }
}

export const config = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
