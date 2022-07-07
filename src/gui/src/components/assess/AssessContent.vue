<template>
  <v-col class="overflow-hidden">
    <v-container fluid>
      <loader
        v-if="itemsLoaded.length < items.length"
        label="loading news items"
      />

      <transition name="empty-list-transition" mode="out-in">
        <v-row v-if="!filteredItems.length">
          <v-col cols="12" class="empty-list-notification">
            <v-icon x-large> mdi-circle-off-outline </v-icon>
            <span v-if="getTotalNumber().length">
              The currently selected filters do not yield any results. Try
              changing the filters.
            </span>
            <span v-else> No elements to display. </span>
          </v-col>
        </v-row>

        <transition-group
          name="news-items-grid"
          tag="div"
          class="row d-flex align-stretch row--dense topics-grid-container"
          v-else
          appear
        >
          <card-news-item
            v-for="(newsItem, index) in filteredItems"
            :key="newsItem.id"
            :newsItem="newsItem"
            :position="index"
            :topicsList="getTopicSelectionList()"
            :selected="getNewsItemsSelection().includes(newsItem.id)"
            :topicView="topicView"
            :sharingSetView="sharingSetView"
            @deleteItem="removeAndDeleteNewsItem(newsItem.id)"
            @removeFromTopic="removeFromTopic(newsItem.id)"
            @selectItem="selectNewsItem(newsItem.id)"
            @upvoteItem="upvoteNewsItem(newsItem.id)"
            @downvoteItem="downvoteNewsItem(newsItem.id)"
            @init="itemsLoaded.push(newsItem.id)"
          ></card-news-item>
        </transition-group>
      </transition>
    </v-container>

    <!-- TODO: Loader not working -->
    <loader
      v-if="itemsToLoad > itemsLoaded.length"
      label="loading further news items"
    />
    <div
      v-else
      class="text-subtitle-1 text-center dark-grey--text text--lighten-2 mt-3"
    >
      <v-icon left color="primary">mdi-checkbox-marked-circle-outline</v-icon>
      All items loaded.
    </div>
    <div v-intersect.quiet="infiniteScrolling"></div>

    <v-expand-transition>
      <assess-selection-toolbar
        class="px-1 pt-2 pb-3"
        v-if="activeSelection"
        :selection="getNewsItemsSelection()"
      ></assess-selection-toolbar>
    </v-expand-transition>
  </v-col>
</template>

<script>
import CardNewsItem from '@/components/common/card/CardNewsItem'
import Loader from '@/components/common/Loader'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar'

import { mapState, mapGetters, mapActions } from 'vuex'
import { filterSearch, filterDateRange, filterTags } from '@/utils/ListFilters'
import moment from 'moment'

export default {
  name: 'AssessContent',
  components: {
    CardNewsItem,
    Loader,
    AssessSelectionToolbar
  },
  props: {
    topicView: Boolean,
    sharingSetView: Boolean,
    itemsToLoad: Number
  },
  data: () => ({
    itemsLoaded: [],
    reloading: false,
    items: []
  }),
  methods: {
    ...mapActions('assess', [
      'deleteNewsItem',
      'selectNewsItem',
      'upvoteNewsItem',
      'downvoteNewsItem',
      'removeTopicFromNewsItem'
    ]),
    ...mapGetters('assess', [
      'getTotalNumber',
      'getNewsItems',
      'getNewsItemById',
      'getNewsItemsSelection',
      'getNewsItemsByTopicId',
      'getNewsItemsByTopicList'
    ]),
    ...mapGetters('dashboard', ['getTopicSelectionList', 'getNewsItemIds']),

    removeAndDeleteNewsItem (id) {
      this.items = this.items.filter((x) => x.id !== id)
      this.deleteNewsItem(id)
    },

    removeFromTopic (newsItemId) {
      if (this.topicView || this.sharingSetView) {
        const topic = this.scope.topics
        const sharingSet = this.scope.sharingSets
        const topicId = topic ? topic[0].id : sharingSet[0].id
        this.removeTopicFromNewsItem({ newsItemId, topicId })
        this.items = this.items.filter((x) => x.id !== newsItemId)
      }
    },

    infiniteScrolling (entries, observer, isIntersecting) {
      if (
        this.itemsLoaded.length >= this.items.length &&
        isIntersecting &&
        this.itemsToLoad > this.itemsLoaded.length
      ) {
        this.reloading = true
        // TODO: Make it async
        this.updateNewsItems()
        this.reloading = false
      }
    },

    // TODO: Call API via Store
    // + pass filter parameter for presorting
    updateNewsItems () {
      const topics = this.scope.topics
      const sharingSets = this.scope.sharingSets

      let totalTopicItems = []
      topics.forEach((topic) => {
        const topicItems = this.getNewsItemIds()(topic.id)
        totalTopicItems = [...new Set([...totalTopicItems, ...topicItems])]
      })

      let totalSharingSetItems = []
      sharingSets.forEach((sharingSet) => {
        const sharingSetItems = this.getNewsItemIds()(sharingSet.id)
        totalSharingSetItems = [
          ...new Set([...totalSharingSetItems, ...sharingSetItems])
        ]
      })

      let scopedItems = []
      if (topics.length && sharingSets.length) {
        scopedItems = totalTopicItems.filter((id) =>
          totalSharingSetItems.includes(id)
        )
      } else if (topics.length) {
        scopedItems = totalTopicItems
      } else if (this.scope.sharingSets.length) {
        scopedItems = totalSharingSetItems
      }

      let limit = 10

      let chunkedData = [...this.items].filter((item) =>
        scopedItems.includes(item.id)
      )

      if (scopedItems.length) {
        scopedItems.forEach((itemId) => {
          if (!this.itemsLoaded.includes(itemId)) {
            if (limit === 0) return false
            limit--
          }
          chunkedData = [
            ...new Set([...chunkedData, this.getNewsItemById()(itemId)])
          ]
        })
      } else {
        chunkedData = this.getNewsItems()
      }
      this.items = chunkedData
    }
  },

  computed: {
    ...mapState('filter', {
      scope: (state) => state.newsItemsFilter.scope,
      filter: (state) => state.newsItemsFilter.filter,
      order: (state) => state.newsItemsFilter.order
    }),

    filteredItems () {
      let filteredData = [...this.items]

      // TODO: Filtering should be done via API - only keep sorting on client

      filteredData = filteredData.filter((item) => {
        // Only show
        const onlyShowAttr = this.filter.attributes.selected
        if (onlyShowAttr.includes('unread') && item.read) return false
        if (onlyShowAttr.includes('important') && !item.important) return false
        if (onlyShowAttr.includes('shared') && !item.shared) return false
        if (
          onlyShowAttr.includes('selected') &&
          !this.getNewsItemsSelection().includes(item.id)
        ) {
          return false
        }

        // Tags filter
        const tagsResult =
          !this.filter.tags.selected.length ||
          filterTags(
            item.tags,
            this.filter.tags.selected,
            this.filter.tags.andOperator
          )
        if (!tagsResult) return false

        // Date filter
        const dateResult =
          this.filter.date.selected === 'all' ||
          filterDateRange(
            item.published,
            this.filter.date.selected,
            this.filter.date.range
          )
        if (!dateResult) return false

        // Search filter
        const searchResult =
          !this.filter.search ||
          filterSearch([item.title, item.summary], this.filter.search)
        if (!searchResult) return false

        return true
      })

      // SORTING
      filteredData.sort((x, y) => {
        const directionModifier =
          this.order.selected.direction === 'asc' ? 1 : -1

        if (x === y) return 0

        switch (this.order.selected.type) {
          case 'relevanceScore':
            return x.relevanceScore < y.relevanceScore
              ? -1 * directionModifier
              : 1 * directionModifier
          case 'publishedDate':
            return (
              (moment(x.published, 'DD/MM/YYYY hh:mm:ss') -
                moment(y.published, 'DD/MM/YYYY hh:mm:ss')) *
              directionModifier
            )
        }
      })

      this.$store.dispatch('updateItemCount', {
        total: this.getTotalNumber(),
        filtered: filteredData.length
      })

      return filteredData
    },

    activeSelection () {
      return this.getNewsItemsSelection().length > 0
    }
  },

  mounted () {
    // Once this component is loaded load the initial data
    this.updateNewsItems(false)
  },

  updated () {
    console.log('component re-rendered!')
  },

  watch: {
    scope: {
      handler () {
        // Update news items based on the selected scope
        this.updateNewsItems()
      },
      deep: true
    }
  }
}
</script>
