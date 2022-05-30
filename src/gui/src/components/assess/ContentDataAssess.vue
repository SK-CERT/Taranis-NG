<template>
  <div class="overflow-hidden">
    <transition-group
      name="topics-grid"
      tag="div"
      class="row d-flex align-stretch row--dense topics-grid-container"
      appear
    >
      <card-news-item
        v-for="(newsItem, index) in filteredNewsItems"
        :key="newsItem.id"
        :newsItem="newsItem"
        :position="index"
        @selectCard="selectCard"
      ></card-news-item>
    </transition-group>

    <v-expand-transition>
      <selection-toolbar
        v-if="activeSelection"
        :selection="selection"
      ></selection-toolbar>
    </v-expand-transition>
  </div>
</template>

<script>
import CardNewsItem from '@/components/common/card/CardNewsItem'
import SelectionToolbar from '@/components/assess/SelectionToolbar'

import { mapState } from 'vuex'
import { filterSearch, filterDateRange, filterTags } from '@/utils/ListFilters'
import { xor } from 'lodash'
import moment from 'moment'

import { faker } from '@faker-js/faker'

export default {
  name: 'ContentDataAssess',
  components: {
    // CardAssess,
    // NewsItemSingleDetail,
    // NewsItemDetail,
    // NewsItemAggregateDetail,
    CardNewsItem,
    SelectionToolbar
  },
  props: {
    // analyze_selector: Boolean,
    // selection: Array,
    // selfID: String,
    // data_set: String
  },
  data: () => ({
    news_items_data: [],
    news_items_data_loaded: false,
    selection: []
  }),
  methods: {
    selectCard (itemId) {
      var index = this.news_items_data.findIndex((x) => x.id === itemId)
      this.news_items_data[index].selected =
        !this.news_items_data[index].selected

      this.selection = xor(this.selection, [itemId])
    },

    infiniteScrolling (entries, observer, isIntersecting) {
      if (this.news_items_data_loaded && isIntersecting) {
        this.updateData(true, false)
      }
    },

    // showItemDetail (news_item) {
    //   this.$root.$emit('change-state', 'SHOW_ITEM')
    //   this.$refs.newsItemDetail.open(news_item)
    // },

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

      this.$store
        .dispatch('getNewsItemsByGroup', {
          group_id: group,
          data: {
            filter: this.news_items_filter,
            offset: offset,
            limit: limit
          }
        })
        .then(() => {
          this.news_items_data = this.news_items_data.concat(
            this.$store.getters.getNewsItems.items
          )
          this.$emit(
            'new-data-loaded',
            this.$store.getters.getNewsItems.total_count
          )
          setTimeout(() => {
            this.$emit('card-items-reindex')
          }, 200)
          setTimeout(() => {
            this.news_items_data_loaded = true
          }, 1000)
        })
    },

    checkFocus (pos) {
      this.$root.$emit('check-focus', pos)
    },

    news_items_updated () {
      // only update items when not in selection mode
      if (!this.activeSelection) {
        this.updateData(false, true)
      }
    },    
  },

  computed: {
    ...mapState('newsItemsFilter', ['filter', 'order']),

    filteredNewsItems () {
      let filteredData = [...this.news_items_data]

      // SEARCH
      filteredData = filteredData.filter((item) => {
        return (
          !this.filter.search ||
          filterSearch([item.title, item.excerpt], this.filter.search)
        )
      })

      // DATE
      filteredData = filteredData.filter((item) => {
        return (
          this.filter.date.selected === 'all' ||
          filterDateRange(
            item.published,
            this.filter.date.selected,
            this.filter.date.range
          )
        )
      })

      // TAGS
      filteredData = filteredData.filter((item) => {
        return (
          this.filter.tags.selected.includes('all') ||
          filterTags(
            item.tags,
            this.filter.tags.selected,
            this.filter.tags.andOperator
          )
        )
      })

      // ONLY SHOW
      this.filter.attributes.selected.forEach((type) => {
        filteredData = filteredData.filter((item) => {
          switch (type) {
            case 'unread':
              return !item.read
            case 'important':
              return item.important
            case 'recommended':
              return item.recommended
            case 'analysis':
              return item.inAnalysis
            case 'selected':
              return item.selected
          }
        })
      })

      // SORTING
      filteredData.sort((x, y) => {
        
        const directionModifier =
          this.order.selected.direction === 'asc' ? 1 : -1

        if (x === y) return 0

        switch (this.order.selected.type) {
          case 'relevanceScore':
            return parseInt(x.relevanceScore) < parseInt(y.relevanceScore)
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
        total: this.news_items_data.length,
        filtered: filteredData.length
      })

      return filteredData
    },

    activeSelection () {
      return this.selection.length > 0
    }

  },

  mounted () {
    // this.$root.$on('news-items-updated', this.news_items_updated)
    // this.$root.$on('force-reindex', this.forceReindex)

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
      'porro ad nihil iusto iure',
      'modi odit',
      'aliquam nulla',
      'aut exercitationem',
      'quia reiciendis dolor',
      'necessitatibus at quidem',
      'maiores assumenda modi aut',
      'rerum sit'
    ]

    var numberOfDummyTopics = 40
    var dummyData = []

    for (var i = 1; i < numberOfDummyTopics; i++) {
      var sourceDomain = faker.internet.domainName()
      var entry = {
        id: i,
        relevanceScore: faker.commerce.price(0, 100, 0),
        title: faker.hacker.phrase(),
        excerpt: faker.lorem.paragraph(100),
        tags: faker.random.arrayElements(
          dummyTags,
          Math.floor(Math.random() * (5 - 2 + 1)) + 2
        ),
        published: new Date(String(faker.date.recent(10))),
        collected: new Date(String(faker.date.recent(10))),
        source: {
          domain: sourceDomain,
          url: `${faker.internet.protocol()}://${sourceDomain}/rss/${moment(
            new Date(String(faker.date.recent(10)))
          ).format('YYYY/MM/DD')}/${faker.internet.password(20)}`
        },
        addedBy: faker.lorem.words(1),
        topics: faker.random.arrayElements(
          dummyTopics,
          Math.floor(Math.random() * (5 - 2 + 1)) + 2
        ),
        votes: {
          up: faker.commerce.price(0, 150, 0),
          down: faker.commerce.price(0, 250, 0)
        },
        important: Math.random() < 0.2,
        read: Math.random() < 0.2,
        decorateSource: Math.random() < 0.2,
        recommended: Math.random() < 0.2,
        inAnalysis: Math.random() < 0.2,
        selected: false
      }
      dummyData.push(entry)
    }

    this.news_items_data = dummyData
  }

  // beforeDestroy () {
  //   this.$root.$off('news-items-updated', this.news_items_updated)
  // }
}
</script>
