<template>
  <div>
    <ViewLayout>
      <template v-slot:panel>
        <v-expand-transition>
          <div
            v-if="
              filter.scope.topics.length === 1 ||
              filter.scope.sharingSets.length === 1
            "
          >
            <topic-header-assess v-if="filter.scope.topics.length === 1" />
            <sharing-set-header-assess v-else />
          </div>
        </v-expand-transition>
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
        <!-- :topic="topic" -->
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
import SharingSetHeaderAssess from '@/components/assess/SharingSetHeaderAssess'

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
    SharingSetHeaderAssess,
    NewReportItem
  },
  props: {
    analyze_selector: Boolean
  },
  data: () => ({
    dialog_stack: 0
    // filter: { search: '', tag: '' }
  }),
  mixins: [KeyboardMixin('assess')],
  computed: {
    // ...mapState('assess', ['newsItems']),
    ...mapState('newsItemsFilter', ['filter']),

    topic () {
      return this.getTopicById()(parseInt(this.filter.scope.topics[0].id))
    },

    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    }
  },
  methods: {
    ...mapActions('assess', ['updateNewsItems']),
    ...mapActions('newsItemsFilter', ['resetNewsItemsFilter']),
    ...mapGetters('dashboard', ['getTopicById', 'getTopicTitleById']),

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

    this.resetNewsItemsFilter()
    const topicId = parseInt(this.$route.query.topic)
    const topic = this.getTopicById()(topicId)
    if (topic.isSharingSet) {
      this.filter.scope.sharingSets = [{ id: topicId, title: topic.title }]
      this.filter.scope.topics = []
    } else {
      this.filter.scope.sharingSets = []
      this.filter.scope.topics = [{ id: topicId, title: topic.title }]
    }
  }
}
</script>
