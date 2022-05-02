import { getDashboardData } from '@/api/dashboard'

const state = {
  dashboard_data: {
    total_news_items: 0,
    total_products: 0,
    report_items_completed: 0,
    report_items_in_progress: 0,
    total_database_items: 0,
    latest_collected: '',
    tag_cloud: {}
  },
  filterList: {}
}

const actions = {

  getAllDashboardData (context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  }
}

const mutations = {

  setDashboardData (state, data) {
    state.dashboard_data = data
  },

  setFilterList (state, data) {
    state.filterList = data
  }

}

const getters = {

  getDashboardData (state) {
    return state.dashboard_data
  },

  getFilterList (state) {
    return state.filterList
  }

}

export const dashboard = {
  state,
  actions,
  mutations,
  getters
}
