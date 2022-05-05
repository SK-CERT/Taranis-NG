<template>
    <v-col xs="12" sm="6" md="4" :xl="promValue">
        <card-topic :topic="topic" :topicList="topicList"></card-topic>
    </v-col>
</template>

<script>
import CardTopic from '@/components/common/card/CardTopic'

export default {
  name: 'AdaptiveCardsize',
  components: {
    CardTopic
  },
  props: {
    position: Number,
    topic: {},
    topicList: []
  },
  emits: ['updateTopicList'],
  computed: {
    promValue () {
      if (this.$vuetify.breakpoint.xl) {
        // On extra large displays highlight top 4
        return (this.position < 4) ? 3 : 2
      } else {
        // On smaller displays highlight top 3
        return (this.position < 3) ? 4 : 3
      }
    }
  }
}
</script>
