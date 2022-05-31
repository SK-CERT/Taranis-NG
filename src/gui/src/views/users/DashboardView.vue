<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>
      <DashboardContent />
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import DashboardContent from '@/components/dashboard/DashboardContent'
import { mapState, mapGetters, mapActions } from 'vuex'

import { faker } from '@faker-js/faker'

export default {
  name: 'DashboardView',
  components: {
    ViewLayout,
    DashboardContent
  },
  data: () => ({}),
  methods: {
    ...mapActions('dashboard', ['updateTopics'])
  },
  computed: {},
  mounted () {
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
    var dummyData = []

    for (var i = 1; i < numberOfDummyTopics; i++) {
      var entry = {
        id: i,
        relevanceScore: parseInt(faker.commerce.price(0, 100, 0)),
        title: faker.lorem.words(Math.floor(Math.random() * (5 - 2 + 1)) + 2),
        tags: faker.random.arrayElements(
          dummyTags,
          Math.floor(Math.random() * (5 - 2 + 1)) + 2
        ),
        ai: Math.random() < 0.5,
        hot: Math.random() < 0.2,
        pinned: Math.random() < 0.05,
        lastActivity: new Date(String(faker.date.recent(10))),
        excerpt: faker.lorem.paragraph(),
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
        selected: false
      }
      dummyData.push(entry)
    }

    this.updateTopics(dummyData)
  }
}
</script>
