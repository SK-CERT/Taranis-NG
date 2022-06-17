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
    ...mapActions('dashboard', ['updateTopics', 'unselectAllTopics']),
    ...mapActions('assess', ['deselectAllNewsItems']),
    ...mapActions('newsItemsFilter', ['resetNewsItemsFilter']),
    ...mapActions('topicsFilter', ['resetTopicsFilter']),
    ...mapGetters('dummyData', [
      'getDummyTopics',
      'getDummySharingSets',
      'getDummyNewsItems'
    ])
  },
  computed: {},
  mounted () {
    this.unselectAllTopics()
    this.resetTopicsFilter()
    this.deselectAllNewsItems()
    this.resetNewsItemsFilter()
  }
}
</script>
