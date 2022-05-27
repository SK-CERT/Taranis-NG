import { getField, updateField } from 'vuex-map-fields'

export const newsItemsFilter = {
  namespaced: true,
  state: {
    filter: {
      attributes: [],
      tags: [],
      time: {}
    },
    order: {
      by: '',
      direction: 'desc'
    }
  },
  getters: {
    getField,
  },
  mutations: {
    updateField,
  },
}
