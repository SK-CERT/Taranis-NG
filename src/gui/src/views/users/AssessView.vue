<template>
  <div>
    <ViewLayout>
      <template v-slot:panel>
        <topic-header-assess :topic="topic" :newsItems="newsItems">
        </topic-header-assess>
      </template>
      <template v-slot:content>
        <AssessContent
          card-item="CardAssess"
          selfID="selector_assess"
          data_set="assess"
          ref="contentData"
          :filter="filter"
          @new-data-loaded="newDataLoaded"
          @card-items-reindex="cardReindex"
          @update-news-items-filter="updateFilter"
        />
      </template>
    </ViewLayout>
  </div>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import NewReportItem from '@/components/analyze/NewReportItem'
import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess'
import AssessContent from '@/components/assess/AssessContent'
import TopicHeaderAssess from '@/components/assess/TopicHeaderAssess'

import KeyboardMixin from '../../assets/keyboard_mixin'

import { mapState, mapGetters, mapActions } from 'vuex'

import moment from 'moment'
import { faker } from '@faker-js/faker'

export default {
  name: 'Assess',
  components: {
    ViewLayout,
    ToolbarFilterAssess,
    AssessContent,
    TopicHeaderAssess,
    NewReportItem
  },
  props: {
    analyze_selector: Boolean
  },
  data: () => ({
    dialog_stack: 0,
    filter: { search: '', tag: '' },
    topic: {}
  }),
  mixins: [KeyboardMixin('assess')],
  computed: {
    ...mapState('assess', ['newsItems']),

    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    }
  },
  methods: {
    ...mapActions('assess', ['updateNewsItems']),

    newDataLoaded (count) {
      this.$refs.toolbarFilter.updateDataCount(count)
    },

    updateFilter (filter) {
      this.$refs.contentData.updateFilter(filter)
      this.$store.dispatch('filter', filter)
      this.filter = filter
    },

    cardReindex () {
      this.keyRemaper()

      // this scrolls the page all the way up... it should only scroll to the top of the newly-loaded items
      // setTimeout( ()=>{
      //     this.scrollPos();
      // },1 )

      if (this.focus) {
        this.$refs.contentData.checkFocus(this.pos)
      }
    },

    firstDialog (action) {
      if (action === 'push') {
        this.dialog_stack++
      } else {
        this.dialog_stack--
      }
      if (this.dialog_stack <= 0) {
        this.isItemOpen = false
        this.dialog_stack = 0
      } else {
        this.isItemOpen = true
      }
    }
  },
  watch: {
    $route () {
      this.$refs.contentData.updateData(false, false)
    }
  },
  created () {
    document.addEventListener('keydown', this.keyAction, false)
    const element = document.querySelector('card-item')
    if (element != null) {
      element.addEventListener('click', this.targetClick, false)
    }
  },
  beforeDestroy () {
    document.removeEventListener('keydown', this.keyAction)
    const element = document.querySelector('card-item')
    if (element != null) {
      element.removeEventListener('click')
    }
    this.$root.$off('first-dialog')
    this.$root.$off('clear-cards')
  },
  mounted () {
    if (window.location.pathname.includes('/group/')) {
      this.$refs.contentData.updateData(false, false)
    }

    this.$root.$on('first-dialog', (action) => {
      this.firstDialog(action)
    })

    this.$root.$on('clear-cards', () => {
      const cards = document.querySelectorAll('.card-item')
      cards.forEach((card) => card.remove())
    })

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

    var dummySourceTypes = [
      'RSS',
      'MISP',
      'Web',
      'Twitter',
      'Email',
      'Slack',
      'Atom'
    ]

    var dummySharingSets = [
      'Sharingset One',
      'Sharingset Two',
      'Sharingset Three',
      'Sharingset Four'
    ]

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

    this.topic = {
      id: 0,
      relevanceScore: parseInt(faker.commerce.price(0, 100, 0)),
      title: faker.lorem.words(Math.floor(Math.random() * (5 - 2 + 1)) + 2),
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      ai: Math.random() < 0.25,
      hot: Math.random() < 0.15,
      pinned: Math.random() < 0.05,
      originator: `${faker.name.firstName()} ${faker.name.lastName()}`,
      lastActivity: new Date(String(faker.date.recent(10))),
      excerpt: faker.lorem.paragraph(15),
      items: {
        total: parseInt(faker.commerce.price(70, 200, 0)),
        new: parseInt(faker.commerce.price(0, 70, 0))
      },
      comments: {
        total: parseInt(faker.commerce.price(70, 200, 0)),
        new: parseInt(faker.commerce.price(0, 70, 0))
      },
      votes: {
        up: parseInt(faker.commerce.price(0, 150, 0)),
        down: parseInt(faker.commerce.price(0, 250, 0))
      },
      shared: Math.random() < 0.15,
      relatedTopics: faker.random.arrayElements(
        dummyTopics,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      keywords: faker.random.words(Math.random() * (16 - 6 + 1) + 6).split(' '),
      selected: false
    }

    var numberOfDummyItems = Math.floor(Math.random() * (140 - 40 + 1)) + 40
    var dummyData = []

    for (var i = 1; i < numberOfDummyItems; i++) {
      var sourceDomain = faker.internet.domainName()
      const shared = Math.random() < 0.2
      var entry = {
        id: i,
        relevanceScore: faker.commerce.price(0, 100, 0),
        title: faker.hacker.phrase(),
        excerpt: faker.lorem.paragraph(100),
        tags: faker.random.arrayElements(
          dummyTags,
          Math.floor(Math.random() * (5 - 2 + 1)) + 2
        ),
        published: new Date(String(faker.date.recent(80))),
        collected: new Date(String(faker.date.recent(20))),
        source: {
          domain: sourceDomain,
          url: `${faker.internet.protocol()}://${sourceDomain}/rss/${moment(
            new Date(String(faker.date.recent(50)))
          ).format('YYYY/MM/DD')}/${faker.internet.password(20)}`,
          type: dummySourceTypes[Math.floor(Math.random() * 7)]
        },
        addedBy: faker.lorem.words(1),
        topics: faker.random.arrayElements(
          dummyTopics,
          Math.floor(Math.random() * (5 - 2 + 1)) + 2
        ),
        votes: {
          up: parseInt(faker.commerce.price(0, 150, 0)),
          down: parseInt(faker.commerce.price(0, 250, 0))
        },
        important: Math.random() < 0.2,
        read: Math.random() < 0.2,
        decorateSource: Math.random() < 0.2,
        recommended: Math.random() < 0.2,
        inAnalysis: Math.random() < 0.2,
        shared: shared,
        sharingSets: shared
          ? faker.random.arrayElements(
            dummySharingSets,
            Math.floor(Math.random() * (3 - 1 + 1)) + 1
          )
          : [],
        restricted: Math.random() < 0.2,
        selected: false
      }
      dummyData.push(entry)
    }

    this.updateNewsItems(dummyData)
  }
}
</script>
