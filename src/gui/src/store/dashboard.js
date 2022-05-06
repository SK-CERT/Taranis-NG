import { actions } from './topics/actions'
import { getters } from './topics/getters'
import { mutations } from './topics/mutations'

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
  filterList: {},
  filter: {},
  sortBy: {},
  topicList: {
    original: [],
    accumulated: []
  }
}

export const dashboard = {
  state,
  actions,
  mutations,
  getters
}
