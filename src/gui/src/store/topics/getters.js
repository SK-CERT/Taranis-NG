export const getters = {

  getDashboardData (state) {
    return state.dashboard_data
  },

  getOriginalTopicList (state) {
    return state.topicList.original
  },

  getAccumulatedTopicList (state) {
    return state.topicList.accumulated
  },

  getFilterList (state) {
    return state.filterList
  },

  getSortBy (state) {
    return state.sortBy
  },

  getFilter (state) {
    return state.filter
  }

}
