import { getDashboardData } from '@/api/dashboard'
import { getField, updateField } from 'vuex-map-fields'
import { xor } from 'lodash'

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
  topics: [],
  topicSelection: []
}

const actions = {

  getAllDashboardData (context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  updateTopics (context, topics) {
    context.commit('UPDATE_TOPICS', topics)
  },

  pinTopic (context, id) {
    context.commit('PIN_TOPIC', id)
  },

  upvoteTopic (context, id) {
    context.commit('UPVOTE_TOPIC', id)
  },

  downvoteTopic (context, id) {
    context.commit('DOWNVOTE_TOPIC', id)
  },

  selectTopic (context, id) {
    context.commit('SELECT_TOPIC', id)
  },

  unselectAllTopics (context, id) {
    context.commit('UNSELECT_ALL_TOPICS', id)
  }

  // selectTopic(context, id) {
  //   context.commit('toggleSelect', id)
  // },

  // sortTopics(context, data) {
  //   context.commit('applySortby', data)
  //   context.commit('sortTopics')
  // },

  // filterTopics(context, data) {
  //   context.commit('applyFilter', data)
  //   context.commit('resetList')
  //   context.commit('filterTopics')
  //   context.commit('filterTopicsByTags')
  //   context.commit('sortTopics')
  // },

  // filterTopicsByTags(context, data) {
  //   context.commit('applyTagsFilter', data)
  //   context.commit('resetList')
  //   context.commit('filterTopics')
  //   context.commit('filterTopicsByTags')
  //   context.commit('sortTopics')
  // }

}

const mutations = {

  updateField,

  UPDATE_TOPICS (state, topics) {
    state.topics = topics
  },

  PIN_TOPIC (state, id) {
    const index = state.topics.findIndex((x) => x.id === id)
    state.topics[index].pinned =
      !state.topics[index].pinned
  },

  UPVOTE_TOPIC (state, id) {
    const index = state.topics.findIndex((x) => x.id === id)
    state.topics[index].votes.up += 1
  },

  DOWNVOTE_TOPIC (state, id) {
    const index = state.topics.findIndex((x) => x.id === id)
    state.topics[index].votes.down += 1
  },

  SELECT_TOPIC (state, id) {
    state.topicSelection = xor(state.topicSelection, [id])
  },

  UNSELECT_ALL_TOPICS (state) {
    state.topicSelection = []
    state.topics.forEach(element => {
      element.selected = false
    })
  }

  // toggleSelect(state, id) {
  //   var index = state.topicList.accumulated.findIndex((x) => x.id === id)
  //   state.topicList.accumulated[index].selected =
  //     !state.topicList.accumulated[index].selected
  // },

  // sortTopics(state) {
  //   var type = state.sortBy.selected.type
  //   var direction = state.sortBy.selected.direction
  //   var keepPinned = state.sortBy.keepPinned

  //   state.topicList.accumulated.sort((x, y) => {
  //     // Get properties
  //     var elements = getElements(type, x, y)

  //     // Set direction
  //     elements = direction === 'asc' ? elements : [elements[1], elements[0]]

  //     // Apply pinned sorting
  //     if (keepPinned) {
  //       if (x.pinned && !y.pinned) return -1
  //       if (!x.pinned && y.pinned) return 1
  //     }

  //     // Apply property sorting
  //     return propertySorting(type, elements)
  //   })
  // },

  // // Setters
  // setDashboardData(state, data) {
  //   state.dashboard_data = data
  // },

}

const getters = {

  getField,

  getTopics (state) {
    return state.topics
  },

  getTopicSelection (state) {
    return state.topicSelection
  },

  getDashboardData (state) {
    return state.dashboard_data
  },

  getTopicById: (state) => (id) => {
    return state.topics.find(topic => topic.id === id)
  }
}

export const dashboard = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
