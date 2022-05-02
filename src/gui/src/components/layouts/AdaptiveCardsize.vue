<template>
    <v-col cols="12" sm="6" :md="promValue" :xl="(promValue-1)">
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
  emits: ['updatePinned'],
  computed: {
    promValue () {
      var limit = ((this.$vuetify.breakpoint.xl) ? 4 : 3)
      return (((this.position + 1) > limit) ? 3 : 4)
    }
  }
}
</script>
