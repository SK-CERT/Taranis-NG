<template>
    <v-card tile elevation="4" outlined height="100%" :class="[
    'pa-5',
    'pl-5',
    'align-self-stretch',
    'topic',
    'primary--text',
    {
        'pinned-topic': topic.pinned,
        'selected': topic.selected,
    }]"
    @click="selectCard"
    >
        <div class="status-bar" v-if="topic.hot" :class="[
        {
            'hot-topic': topic.hot
        }]">
        </div>
        <v-container column style="height: 100%">

            <v-row no-gutters style="height: 100%">
                <v-col class="d-flex flex-column" align-self="start" style="height: 100%">

                    <!-- Header -->

                    <v-row class="flex-grow-0">
                        <v-col cols="10" class="mr-auto mt-1">
                            <tag-mini label="AI" v-show="topic.ai" />
                            <span class="last-activity font-weight-light dark-grey--text">Last activity: </span>
                            <span class="last-activity font-weight-bold dark-grey--text"> {{ topic.lastActivity }} </span>
                        </v-col>

                        <v-col cols="2" class="text-right">
                            <v-btn fab depressed outlined x-small color="grey" :class="['fab-pin', {'pinned': topic.pinned,}]" @click.native.capture="pinToTop($event)">
                                <v-icon>$awakePin</v-icon>
                            </v-btn>
                        </v-col>
                    </v-row>

                    <!-- Title -->

                    <v-row class="flex-grow-0 mt-1">
                        <v-col>
                            <h2 class="font-weight-bold headline dark-grey--text text-capitalize">
                                {{ topic.title }}
                            </h2>
                        </v-col>
                    </v-row>

                    <v-row class="flex-grow-0 mt-1">
                        <v-col>
                            <tag-topic v-for="tag in topic.tags" :key="tag.label" :tag="tag" />
                        </v-col>
                    </v-row>

                    <!-- spacer -->

                    <v-spacer></v-spacer>

                    <!-- Excerpt -->

                    <v-row class="flex-grow-0 mt-2">
                        <v-col>
                            <p class="font-weight-light dark-grey--text topic-excerpt">
                                {{ topic.summary }}
                            </p>
                        </v-col>
                    </v-row>

                    <!-- Footer -->

                    <v-row no-gutter wrap align="center" justify="end" class="flex-grow-0 mt-0">
                        <v-col cols="12" md="8" class="mx-0 d-flex justify-start">
                            <v-container class="mx-0 pa-0">
                                <v-row class="mx-0">
                                    <v-col cols="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small>mdi-file-outline</v-icon>
                                        <span class="text-caption font-weight-light dark-grey--text">{{ topic.items.total }} /</span>
                                        <span class="text-caption font-weight-bold dark-grey--text">{{ topic.items.new }}</span>
                                    </v-col>
                                    <v-col cols="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small color="awake-green-color">mdi-arrow-up-circle-outline</v-icon>
                                        <span class="text-caption font-weight-light dark-grey--text">{{ topic.votes.up }}</span>
                                    </v-col>
                                    <v-col cols="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small>mdi-message-outline</v-icon>
                                        <span class="text-caption font-weight-light dark-grey--text">{{ topic.comments.total }} /</span>
                                        <span class="text-caption font-weight-bold dark-grey--text">{{ topic.comments.new }}</span>
                                    </v-col>
                                    <v-col cols="6" class="pa-0 pt-0 pr-1">
                                        <v-icon left small color="awake-red-color">mdi-arrow-down-circle-outline</v-icon>
                                        <span class="text-caption font-weight-light dark-grey--text">{{ topic.votes.down }}</span>
                                    </v-col>
                                </v-row>
                            </v-container>
                        </v-col>
                        <v-col cols="12" md="4" class="mx-0 d-flex justify-end">
                            <v-btn outlined class="text-lowercase btn-view-topic mt-1" @click.native.capture="viewTopic($event)">
                                <v-icon left>mdi-eye-outline</v-icon>
                                view topic
                            </v-btn>
                        </v-col>
                    </v-row>

                </v-col>
            </v-row>
        </v-container>
    </v-card>
</template>

<script>
import TagMini from '@/components/common/tags/TagMini'
import TagTopic from '@/components/common/tags/TagTopic'

export default {
  name: 'CardTopic',
  components: {
    TagMini,
    TagTopic
  },
  props: {
    topic: {}
  },
  data: () => ({
  }),
  computed: {
  },
  methods: {
    selectCard: function () {
      this.$store.dispatch('selectTopic', this.topic.id)
    },
    pinToTop: function (event) {
      event.stopPropagation()
      this.$store.dispatch('pinTopic', this.topic.id)
    },
    viewTopic: function (event) {
      event.stopPropagation()
      console.log('view Topics clicked')
    }
  }
}
</script>
