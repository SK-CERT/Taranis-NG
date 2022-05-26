import { getDashboardData } from '@/api/dashboard'

export const actions = {

  getAllDashboardData (context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  pinTopic (context, id) {
    context.commit('togglePin', id)
    context.commit('sortTopics')
  },

  selectTopic (context, id) {
    context.commit('toggleSelect', id)
  },

  sortTopics (context, data) {
    context.commit('applySortby', data)
    context.commit('sortTopics')
  },

  filterTopics (context, data) {
    context.commit('applyFilter', data)
    context.commit('resetList')
    context.commit('filterTopics')
    context.commit('filterTopicsByTags')
    context.commit('sortTopics')
  },

  filterTopicsByTags (context, data) {
    context.commit('applyTagsFilter', data)
    context.commit('resetList')
    context.commit('filterTopics')
    context.commit('filterTopicsByTags')
    context.commit('sortTopics')
  }

}
