import { getField, updateField } from 'vuex-map-fields'

export const newsItemsFilter = {
  namespaced: true,
  state: {
    filter: {
      search: '',
      attributes: {
        selected: []
      },
      tags: {
        andOperator: true,
        selected: ['all']
      },
      date: {
        range: [],
        selected: 'all'
      },
      scope: {
        topics: [],
        sharingSets: [],
        sources: []
      }

    },
    order: {
      selected: {}
    }
  },
  getters: {
    getField
  },
  mutations: {
    updateField
  }
}
