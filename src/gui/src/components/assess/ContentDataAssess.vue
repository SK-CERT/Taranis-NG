<template>
    <transition-group name="topics-grid" tag="div" class="row d-flex align-stretch row--dense topics-grid-container" appear>
        <card-news-item
          v-for="(newsItem, index) in filteredNewsItems"
          :key="newsItem.id"
          :newsItem="newsItem"
          :position="index"
        ></card-news-item>
      </transition-group>

    <!-- <v-container class="selector_assess" :id="selfID">
        <component v-bind:is="cardLayout()" v-for="(news_item,i) in news_items_data" :card="news_item"
                   :key="i" :analyze_selector="analyze_selector"
                   :preselected="preselected(news_item.id)"
                   :word_list_regex="regexWordList"
                   :data_set="data_set"
                   :filter="filter"
                   @show-single-aggregate-detail="showSingleAggregateDetail(news_item)"
                   @show-aggregate-detail="showAggregateDetail(news_item)"
                   @show-item-detail="showItemDetail"
                   @aggregate-open="setAggregateOpen"
                   @update-news-items-filter="updateFilter"
                   ref="card"
                   :aggregate_opened="aggregateOpen(news_item)"
                   @check-focus="checkFocus"
        >
        </component>
        <v-card v-intersect.quiet="infiniteScrolling"></v-card>
        <NewsItemSingleDetail ref="newsItemSingleDetail"/>
        <NewsItemDetail ref="newsItemDetail"/>
        <NewsItemAggregateDetail ref="newsItemAggregateDetail"/>
    </v-container> -->

</template>

<script>
import CardAssess from './CardAssess'
import NewsItemSingleDetail from '@/components/assess/NewsItemSingleDetail'
import NewsItemDetail from '@/components/assess/NewsItemDetail'
import NewsItemAggregateDetail from '@/components/assess/NewsItemAggregateDetail'

import CardNewsItem from '@/components/common/card/CardNewsItem'

import { mapState } from 'vuex';

import { faker } from '@faker-js/faker'
import moment from 'moment'

export default {
  name: 'ContentDataAssess',
  components: {
    CardNewsItem,
    CardAssess,
    NewsItemSingleDetail,
    NewsItemDetail,
    NewsItemAggregateDetail
  },
  props: {
    analyze_selector: Boolean,
    selection: Array,
    cardItem: String,
    selfID: String,
    data_set: String,
    filter: Object
  },
  data: () => ({
    news_items_data: [],
    news_items_data_loaded: false,
    news_items_filter: {
      search: '',
      range: 'ALL',
      read: false,
      important: false,
      relevant: false,
      in_analyze: false,
      sort: 'DATE_DESC'
    },
    aggregate_open: [],
    filterAttributeOptions: [
      { label: 'unread', icon: '$awakeUnread' },
      { label: 'tagged as important', icon: '$awakeImportant' },
      { label: 'recommended', icon: 'mdi-star-outline' },
      { label: 'items in analysis', icon: '$awakeReport' }
    ]
  }),
  methods: {
    cardLayout: function () {
      return this.cardItem
    },

    preselected (item_id) {
      if (this.selection != null) {
        for (let i = 0; i < this.selection.length; i++) {
          if (this.selection[i].id === item_id) {
            return true
          }
        }
      }
      return false
    },

    infiniteScrolling (entries, observer, isIntersecting) {
      if (this.news_items_data_loaded && isIntersecting) {
        this.updateData(true, false)
      }
    },

    showSingleAggregateDetail (news_item) {
      this.$root.$emit('change-state', 'SHOW_ITEM')
      this.$refs.newsItemSingleDetail.open(news_item)
    },

    showAggregateDetail (news_item) {
      this.$root.$emit('change-state', 'SHOW_ITEM')
      this.$refs.newsItemAggregateDetail.open(news_item)
    },

    showItemDetail (news_item) {
      this.$root.$emit('change-state', 'SHOW_ITEM')
      this.$refs.newsItemDetail.open(news_item)
    },

    updateData (append, reload_all) {
      this.news_items_data_loaded = false

      if (append === false) {
        this.news_items_data = []
      }

      let offset = this.news_items_data.length
      let limit = 20
      if (reload_all) {
        offset = 0
        if (this.news_items_data.length > limit) {
          limit = this.news_items_data.length
        }
        this.news_items_data = []
      }

      let group = ''

      if (this.analyze_selector) {
        group = this.$store.getters.getCurrentGroup
      } else {
        if (window.location.pathname.includes('/group/')) {
          const i = window.location.pathname.indexOf('/group/')
          const len = window.location.pathname.length
          group = window.location.pathname.substring(i + 7, len)
          this.$store.dispatch('changeCurrentGroup', group)
        }
      }

      this.$store.dispatch('getNewsItemsByGroup', {
        group_id: group,
        data: {
          filter: this.news_items_filter,
          offset: offset,
          limit: limit
        }
      }).then(() => {
        this.news_items_data = this.news_items_data.concat(this.$store.getters.getNewsItems.items)
        this.$emit('new-data-loaded', this.$store.getters.getNewsItems.total_count)
        setTimeout(() => {
          this.$emit('card-items-reindex')
        }, 200)
        setTimeout(() => {
          this.news_items_data_loaded = true
        }, 1000)
      })
    },

    updateFilter (filter) {
      Object.assign(this.news_items_filter, filter)
      this.updateData(false, false)
    },

    setAggregateOpen (folder) {
      if (!this.aggregate_open.length) {
        this.aggregate_open.push(folder.id)
      } else if (folder.opened === false) {
        const close = this.aggregate_open.indexOf(folder.id)
        this.aggregate_open.splice(close, 1)
      } else {
        this.aggregate_open.push(folder.id)
      }
    },

    checkFocus (pos) {
      this.$root.$emit('check-focus', pos)
    },

    news_items_updated () {
      // only update items when not in selection mode
      if (!this.multiSelectActive) {
        this.updateData(false, true)
      }
    },

    aggregateOpen (folder) {
      for (let i = 0; i < this.aggregate_open.length; i++) {
        if (this.aggregate_open[i] === folder.id && folder.news_items.length !== 1) {
          return true
        }
      }
      return false
    },

    forceReindex () {
      this.$emit('card-items-reindex')
    },

    propertySorting (type, elements) {
      if (elements[0] === elements[1]) return 0
      if (type === 'publishedDate') {
        return (
          moment(elements[0], 'DD/MM/YYYY hh:mm:ss') -
          moment(elements[1], 'DD/MM/YYYY hh:mm:ss')
        )
      } else {
        return parseInt(elements[0]) < parseInt(elements[1]) ? -1 : 1
      }
    }
  },

  computed: {
    
    ...mapState('newsItemsFilter', [
        'filter',
        'order'
    ]),

    filteredNewsItems () {
      // apply filters here
      // var filteredData = this.news_items_data.filter((newsItem) => {
      //   return newsItem.votes.up > 100
      // })
      var filterAttributes = this.$store.getters.getFilterAttributes

      var filteredData = [...this.news_items_data].sort((x, y) => {
        return this.propertySorting('publishedDate', [x.published, y.published])
      })

      // 1) Get filter/sort from store...
      // 2) apply all filters
      // 3) apply sorting
      // ...
      // var filteredData.filter ....
      // filteredData.sort ....
      // return filteredData ....

      return filteredData
    },

    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    },

    regexWordList () {
      const wordsData = this.$store.getters.getProfileWordLists
      let wordListRegex = []
      let chop

      if (wordsData.length) {
        for (let i = 0; i < wordsData.length; i++) {
          for (let j = 0; j < wordsData[i].categories.length; j++) {
            wordsData[i].categories[j].entries.forEach(t => {
              wordListRegex.push(t.value + '|')
            })
          }
        }

        chop = wordListRegex.join('')
        wordListRegex = chop.substring(0, chop.length - 1)
      } else {
        wordListRegex = null
      }

      return wordListRegex
    }
  },

  mounted () {
    this.$root.$on('news-items-updated', this.news_items_updated)
    this.$root.$on('force-reindex', this.forceReindex)

    // Generate Dummy Data
    var dummyTags = [
      { label: 'State', color: Math.floor(Math.random() * 20) },
      { label: 'Cyberwar', color: Math.floor(Math.random() * 20) },
      { label: 'Threat', color: Math.floor(Math.random() * 20) },
      { label: 'DDoS', color: Math.floor(Math.random() * 20) },
      { label: 'Vulnerability', color: Math.floor(Math.random() * 20) },
      { label: 'Java', color: Math.floor(Math.random() * 20) },
      { label: 'CVE', color: Math.floor(Math.random() * 20) },
      { label: 'OT/CPS', color: Math.floor(Math.random() * 20) },
      { label: 'Python', color: Math.floor(Math.random() * 20) },
      { label: 'Privacy', color: Math.floor(Math.random() * 20) },
      { label: 'Social', color: Math.floor(Math.random() * 20) },
      { label: 'APT', color: Math.floor(Math.random() * 20) },
      { label: 'MitM', color: Math.floor(Math.random() * 20) }
    ]

    var dummyTopics = [
      'porro ad nihil iusto iure', 'modi odit', 'aliquam nulla', 'aut exercitationem', 'quia reiciendis dolor', 'necessitatibus at quidem', 'maiores assumenda modi aut', 'rerum sit'
    ]

    var numberOfDummyTopics = 40
    var dummyData = []

    for (var i = 1; i < numberOfDummyTopics; i++) {
      var sourceDomain = faker.internet.domainName()
      var entry = {
        id: i,
        relevanceScore: faker.commerce.price(0, 100, 0),
        title: faker.lorem.words((Math.floor(Math.random() * (10 - 7 + 1)) + 7)),
        excerpt: faker.lorem.paragraph(100),
        tags: faker.random.arrayElements(dummyTags, (Math.floor(Math.random() * (5 - 2 + 1)) + 2)),
        published: moment(new Date(String(faker.date.recent(10)))).format('DD/MM/YYYY hh:mm:ss'),
        collected: moment(new Date(String(faker.date.recent(10)))).format('DD/MM/YYYY hh:mm:ss'),
        source: { domain: sourceDomain, url: `${faker.internet.protocol()}://${sourceDomain}/rss/${moment(new Date(String(faker.date.recent(10)))).format('YYYY/MM/DD')}/${faker.internet.password(20)}` },
        addedBy: faker.lorem.words(1),
        topics: faker.random.arrayElements(dummyTopics, (Math.floor(Math.random() * (5 - 2 + 1)) + 2)),
        votes: { up: faker.commerce.price(0, 150, 0), down: faker.commerce.price(0, 250, 0) },
        important: Math.random() < 0.2,
        read: Math.random() < 0.2,
        decorateSource: Math.random() < 0.2,
        selected: false
      }
      dummyData.push(entry)
    }

    this.news_items_data = dummyData
  },

  beforeDestroy () {
    this.$root.$off('news-items-updated', this.news_items_updated)
  }
}
</script>
