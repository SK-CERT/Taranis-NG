<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>

      <transition-group name="flip-list" tag="div" class="row d-flex align-stretch row--dense">
        <adaptive-cardsize
          v-for="(topic, index) in topicList"
          :key="topic.id"
          :topic="topic"
          :position="index"
          :topicList="topicList"
          @updatePinned="updateTopicList"
        ></adaptive-cardsize>
      </transition-group>

      <v-row no-gutters>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="white"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
                <wordcloud
                  :data="tagCloud"
                  nameKey="word"
                  valueKey="wordQuantity"
                  :color="myColors"
                  :showTooltip="false"
                  :rotate="myRotate"
                  :fontSize="fontSize"
                  :wordClick="wordClickHandler"
                >
                </wordcloud>
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Assess</div>
                <div class="subheading grey--text">
                  Tagcloud for latest collected news items.
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-email-multiple </v-icon>
                <span class="caption grey--text"
                  >There are
                  <strong>{{ getData.totalNewsItems }}</strong> total Assess
                  items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-card-text class="pt-0">
                <div class="title mb-2">Publish</div>
                <!--<div class="subheading grey&#45;&#45;text">Number of pending analyses per hour</div>-->
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="orange">
                  mdi-email-check-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.totalProducts }}</b> products ready
                  for publications.</span
                >
                <v-divider inset></v-divider>
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="4" class="pa-2 mb-4">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Analyze</div>
                <div class="subheading grey--text">Status of report items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-account </v-icon>
                <span class="caption grey--text"
                  >There are
                  <b>{{ getData.reportItemsCompleted }}</b> completed
                  analyses.</span
                >
                <v-divider inset></v-divider>
                <v-icon class="mr-2" color="grey">
                  mdi-account-question-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are
                  <b>{{ getData.reportItemsInProgress }}</b> pending
                  analyses.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Collect</div>
                <div class="subheading grey--text">
                  Collectors activity status
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="green">
                  mdi-lightbulb-off-outline
                </v-icon>
                <span class="caption grey--text"
                  >Collectors are pending at the moment.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
                <span class="caption grey--text"
                  >Last successful run ended at
                  <b>{{ getData.latestCollected }}</b></span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Database</div>
                <div class="subheading grey--text">Number of live items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="blue"> mdi-database </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.totalDatabaseItems }}</b> live
                  items.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-database-check </v-icon>
                <span class="caption grey--text"
                  >There are <b>0</b> archived items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
    </template>
  </ViewLayout>
</template>

<script>
import wordcloud from 'vue-wordcloud'
import ViewLayout from '../../components/layouts/ViewLayout'
import AdaptiveCardsize from '@/components/layouts/AdaptiveCardsize'
// import { mapState } from 'vuex'

import { faker } from '@faker-js/faker'
import moment from 'moment'

export default {
  name: 'DashboardView',
  components: {
    wordcloud,
    ViewLayout,
    AdaptiveCardsize
  },
  data: () => ({
    items: [1, 2, 3, 4, 5, 6, 7, 8, 9],
    myColors: ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'],
    myRotate: { from: 0, to: 0, numOfOrientation: 0 },
    fontSize: [14, 40],
    tagCloud: [],
    labels: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
    value: [200, 675, 410, 390, 310, 460, 250, 240],
    topicList: [],
    filterList: {}
  }),
  computed: {
    getData () {
      return this.$store.getters.getDashboardData
    }
  },
  methods: {
    updateTopicList (newTopicList) {
      this.topicList = newTopicList
    },
    applyFilters () {
      if (Object.keys(this.filterList).length !== 0) {
        for (const [filterName, filters] of Object.entries(this.filterList)) {
          if (filters.apply) {
            console.log(filterName + ' is applied')
          }
        }

        console.log(this.filterList)

        // date: this.date,
        // filterBy: this.filterBy,
        // sortBy: this.sortBy,
        // tags: this.tags
        // alert(JSON.stringify(this.filterList))
      }
    },
    sortByLastActivity (direction) {
      this.topicList.sort((x, y) => {
        const firstElement = (direction === 'asc') ? x.lastActivity : y.lastActivity
        const secondElement = (direction === 'asc') ? y.lastActivity : x.lastActivity
        return moment(new Date(firstElement)).format('DD/MM/YYYY hh:mm:ss') - moment(new Date(secondElement)).format('DD/MM/YYYY hh:mm:ss')
      })
    },
    sortByPinned () {
      this.topicList.sort((x, y) => x.pinned === true ? -1 : y.pinned === true ? 1 : 0)
    },
    wordClickHandler (name, value, vm) {
      window.console.log('wordClickHandler', name, value, vm)
    },
    refreshTagCloud () {
      // Dummy Tag-Cloud data
      this.tagCloud = [{
        name: 'State',
        value: 26
      },
      {
        name: 'Cyberwar',
        value: 19
      },
      {
        name: 'Threat',
        value: 18
      },
      {
        name: 'DDoS',
        value: 16
      },
      {
        name: 'Vulnerability',
        value: 15
      },
      {
        name: 'Java',
        value: 9
      },
      {
        name: 'CVE',
        value: 9
      },
      {
        name: 'OT/CPS',
        value: 9
      },
      {
        name: 'Python',
        value: 6
      }
      ]
    //   this.$store.dispatch('getAllDashboardData').then(() => {
    //     this.tagCloud = this.$store.getters.getDashboardData.tagCloud
    //   })
    }
  },
  mounted () {
    this.refreshTagCloud()

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

    var numberOfDummyTopics = 40

    for (var i = 1; i < numberOfDummyTopics; i++) {
      var entry = {
        id: i,
        title: faker.lorem.words((Math.floor(Math.random() * (5 - 2 + 1)) + 2)),
        tags: faker.random.arrayElements(dummyTags, (Math.floor(Math.random() * (5 - 2 + 1)) + 2)),
        ai: Math.random() < 0.5,
        hot: Math.random() < 0.2,
        pinned: Math.random() < 0.05,
        lastActivity: moment(new Date(String(faker.date.recent(10)))).format('DD/MM/YYYY hh:mm:ss'),
        summary: faker.lorem.paragraph(),
        items: { total: faker.commerce.price(70, 200, 0), new: faker.commerce.price(0, 70, 0) },
        comments: { total: faker.commerce.price(70, 200, 0), new: faker.commerce.price(0, 70, 0) },
        votes: { up: faker.commerce.price(70, 200, 0), down: faker.commerce.price(0, 70, 0) }
      }
      this.topicList.push(entry)
    }

    this.sortByLastActivity('desc')
    this.sortByPinned()

    setInterval(
      function () {
        this.refreshTagCloud()
      }.bind(this),
      600000
    )

    this.$store.commit('setFilterList', this.filterList)

    this.$store.subscribe((mutation, state) => {
      this.filterList = this.$store.getters.getFilterList
      this.applyFilters()
    })
  }
}
</script>
