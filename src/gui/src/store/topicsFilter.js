import { getField, updateField } from 'vuex-map-fields'

export const topicsFilter = {
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
      }
    },
    order: {
      selected: {},
      keepPinned: true
    }
  },
  getters: {
    getField
  },
  mutations: {
    updateField
  }
}
