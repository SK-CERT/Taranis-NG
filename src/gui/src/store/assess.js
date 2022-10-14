import { getNewsItemsAggregates, getOSINTSourceGroupsList, getTopStories, getNewsItemAggregate, getOSINTSourcesList } from '@/api/assess'
import { filter } from '@/store/filter'
import { xor } from 'lodash'

const state = {
  multi_select: false,
  selection: [],
  osint_sources: [],
  osint_source_groups: [],
  default_source_group_id: '',
  filter: {},
  newsItems: { total_count: 0, items: [] },
  newsItemsSelection: [],
  top_stories: []
}

const actions = {

  updateAggregateByID(context, id) {
    return getNewsItemAggregate(id)
      .then(response => {
        context.commit('', response.data)
      })
  },

  updateNewsItemsByGroup(context, newsItemsFilter) {
    return getNewsItemsAggregates(newsItemsFilter)
      .then(response => {
        context.commit('UPDATE_NEWSITEMS', response.data)
      })
  },

  updateNewsItems(context) {
    return getNewsItemsAggregates(filter.state.newsItemsFilter)
      .then(response => {
        context.commit('UPDATE_NEWSITEMS', response.data)
      })
  },

  updateOSINTSources(context) {
    return getOSINTSourcesList()
      .then(response => {
        context.commit('UPDATE_OSINTSOURCES', response.data)
      })
  },

  updateOSINTSourceGroupsList(context) {
    return getOSINTSourceGroupsList()
      .then(response => {
        context.commit('setOSINTSourceGroups', response.data)
        context.commit('setDefaultOSINTSourceGroup', response.data)
      })
  },

  updateTopStories(context) {
    return getTopStories()
      .then(response => {
        context.commit('setTopStories', response.data)
      })
  },

  setNewsItems(context, newsItems) {
    context.commit('UPDATE_NEWSITEMS', newsItems)
  },

  upvoteNewsItem(context, id) {
    context.commit('UPVOTE_NEWSITEM', id)
  },

  downvoteNewsItem(context, id) {
    context.commit('DOWNVOTE_NEWSITEM', id)
  },

  selectNewsItem(context, id) {
    context.commit('SELECT_NEWSITEM', id)
  },

  deleteNewsItem(context, id) {
    context.commit('DELETE_NEWSITEM', id)
  },

  deselectNewsItem(context, id) {
    context.commit('DESELECT_NEWSITEM', id)
  },

  deselectAllNewsItems(context) {
    context.commit('DESELECT_ALL_NEWSITEMS')
  },

  multiSelect(context, data) {
    context.commit('setMultiSelect', data)
  },

  select(context, data) {
    context.commit('addSelection', data)
  },

  deselect(context, data) {
    context.commit('removeSelection', data)
  },

  changeMergeAttr(context, { src, dest }) {
    context.commit('CHANGE_MERGE_ATTR', { src, dest })
  },

  assignSharingSet(context, { items, sharingSet }) {
    context.commit('ASSIGN_SHARINGSET', { items, sharingSet })
  },

  removeStoryFromNewsItem(context, { newsItemId, storyId }) {
    context.commit('REMOVE_TOPIC_FROM_NEWSITEM', { newsItemId, storyId })
  },

  filter(context, data) {
    context.commit('setFilter', data)
  }
}

const mutations = {
  UPDATE_NEWSITEMS(state, newsItems) {
    state.newsItems = newsItems
  },

  UPDATE_OSINTSOURCES(state, osint_sources) {
    state.osint_sources = osint_sources
  },

  SELECT_NEWSITEM(state, id) {
    state.newsItemsSelection = xor(state.newsItemsSelection, [id])
  },

  UPVOTE_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].votes.up += 1
  },

  DOWNVOTE_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].votes.down += 1
  },

  DELETE_NEWSITEM(state, id) {
    state.newsItems = state.newsItems.filter((x) => x.id !== id)
    state.newsItemsSelection = state.newsItemsSelection.filter((x) => x !== id)
  },

  DESELECT_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].selected = false
    state.newsItemsSelection = state.newsItemsSelection.filter((x) => x !== id)
  },

  DESELECT_ALL_NEWSITEMS(state) {
    state.newsItems.items.forEach((newsItem) => { newsItem.selected = false })
    state.newsItemsSelection = []
  },

  ASSIGN_SHARINGSET(state, data) {
    data.items.forEach((item) => {
      const index = state.newsItems.findIndex((x) => x.id === item)
      state.newsItems[index].shared = true
      state.newsItems[index].stories.push(data.sharingSet)
      state.newsItems[index].sharingSets.push(data.sharingSet)
    })
  },

  CHANGE_MERGE_ATTR(state, replacement) {
    replacement.src.forEach(storyToReplace => {
      state.newsItems = [...state.newsItems].map(({ stories, sharingSets, shared, ...rest }) => ({
        stories: stories.map(element => {
          if (storyToReplace === element) {
            return replacement.dest
          }
          return element
        }),
        sharingSets: sharingSets.filter(element => storyToReplace !== element),
        shared: Boolean(sharingSets.length),
        ...rest
      }))
    })
  },

  setMultiSelect(state, enable) {
    state.multi_select = enable
    state.selection = []
  },

  addSelection(state, selected_item) {
    state.selection.push(selected_item)
  },

  removeSelection(state, selectedItem) {
    for (let i = 0; i < state.selection.length; i++) {
      if (state.selection[i].type === selectedItem.type && state.selection[i].id === selectedItem.id) {
        state.selection.splice(i, 1)
        break
      }
    }
  },

  setOSINTSourceGroups(state, osint_source_groups) {
    state.osint_source_groups = osint_source_groups
  },

  setTopStories(state, top_stories) {
    state.top_stories = top_stories
  },

  setDefaultOSINTSourceGroup(state, osint_source_groups) {
    state.default_source_group_id = osint_source_groups.items.filter(value => value.default)[0].id
  },

  setFilter(state, data) {
    state.filter = data
  }
}

const getters = {
  getNewsItems(state) {
    return state.newsItems
  },

  getScopeFilterList(state) {
    return Array.isArray(state.osint_source_groups.items) ? state.osint_source_groups.items.map(value => ({ id: value.id, title: value.name })) : []
  },

  getOSINTSourceGroupList(state) {
    return state.osint_source_groups
  },

  getNewsItemsByStoryId: (state) => (id) => {
    return state.newsItems.filter(newsItem => newsItem.stories.includes(id))
  },

  getNewsItemsByStoryList: (state) => (storiesList) => {
    return state.newsItems.filter(newsItem => {
      return newsItem.stories.some((itemStories) => storiesList.map((story) => story.id).indexOf(itemStories) >= 0)
    })
  },

  getNewsItemById: (state) => (id) => {
    return state.newsItems.find(newsItem => newsItem.id === id)
  },

  getNewsItemsSelection(state) {
    return state.newsItemsSelection
  },

  getMultiSelect(state) {
    return state.multi_select
  },

  getSelection(state) {
    return state.selection
  },

  getOSINTSources(state) {
    return state.osint_sources
  },

  getFilter(state) {
    return state.filter
  }
}

export const assess = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
