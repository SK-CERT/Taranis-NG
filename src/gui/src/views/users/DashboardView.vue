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
    ...mapActions('dashboard', ['updateTopics']),
    ...mapGetters('dummyData', ['getDummyTopics', 'getDummySharingSets', 'getDummyNewsItems'])
  },
  computed: {},
  mounted () {
  }
}
</script>
