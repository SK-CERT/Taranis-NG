<template>
  <v-card>
    <v-container>
      <v-row>
        <v-col cols="12">
          <h2
            class="font-weight-bold headline dark-grey--text text-capitalize pt-3"
          >
            Merge Topics
          </h2>
          The following topics were selected for merging:
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col>
          <v-container fluid>
            <v-row>
              <v-col
                :sm="getColSize"
                v-for="topicId in selection"
                :key="topicId"
                class="d-flex pa-1"
              >
                <v-card
                  elevation="2"
                  tile
                  height="100%"
                  class="align-self-stretch d-flex flex-column merge-topic-details"
                >
                  <v-row justify="start" no-gutters class="flex-grow-0">
                    <v-col>
                      <h4
                        class="font-weight-bold merge-topics-details-title text-capitalize my-2"
                      >
                        {{ getTopicDetails(topicId).title }}
                      </h4>
                    </v-col>
                  </v-row>

                  <v-spacer></v-spacer>
                  <v-divider></v-divider>

                  <v-row
                    justify="end"
                    no-gutters
                    class="flex-grow-0 my-2 merge-topics-details-meta"
                  >
                    <v-col cols="12" v-if="getTopicDetails(topicId).isSharingSet">
                      <v-icon left x-small class="mr-1 flipped-icon"
                        >$awakeShare</v-icon
                      >
                      Shared Set
                    </v-col>
                    <v-col cols="12" v-else>
                      <v-icon left x-small class="mr-1 flipped-icon"
                        >mdi-folder-outline</v-icon
                      >
                      Local Topic
                    </v-col>

                    <v-col cols="12">
                      <v-icon left x-small class="mr-1"
                        >mdi-file-outline</v-icon
                      >
                      {{ getTopicDetails(topicId).items.total }}/
                      <strong>{{ getTopicDetails(topicId).items.new }}</strong>
                    </v-col>
                  </v-row>
                </v-card>
              </v-col>
            </v-row>
          </v-container>
        </v-col>
      </v-row>
    </v-container>

    <v-container class="pb-5 mb-5">
      <v-row>
        <v-col class="py-1">
          <h4
            class="font-weight-bold merge-topics-details-title dark-grey--text text-capitalize my-0"
          >
            Merge Options
          </h4>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="py-2">
          <v-text-field
            hide-details
            dense
            label="Topic Title"
            outlined
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row class="mt-2">
        <!------------->
        <!-- Summary -->
        <!------------->

        <v-col cols="12" class="py-0">
          <v-switch
            v-model="generateSummary"
            inset
            dense
            label="auto-generate summary"
            color="success"
            hide-details
          ></v-switch>
        </v-col>
        <v-expand-transition appear v-if="!generateSummary">
          <v-col cols="12" class="py-0 pt-2">
            <v-textarea label="Summary" hide-details outlined></v-textarea>
          </v-col>
        </v-expand-transition>

        <!--------------------->
        <!-- Keep discussion -->
        <!--------------------->

        <v-col cols="8" class="py-0">
          <v-switch
            v-model="mergeDiscussion"
            inset
            dense
            label="keep discussion"
            color="success"
            hide-details
          ></v-switch>
        </v-col>
        <v-col
          cols="4"
          class="py-0 merge-topics-details-meta grey--text text--darken-2"
        >
          <div class="mt-5 mr-2 text-right">
            <v-icon left x-small class="mr-1 grey--text text--darken-2"
              >mdi-message-outline</v-icon
            >
            {{ mergedTopic.comments.total }}/
            <strong>{{ mergedTopic.comments.new }}</strong>
          </div>
        </v-col>

        <!----------------->
        <!-- Merge Votes -->
        <!----------------->

        <v-col cols="8" class="py-0">
          <v-switch
            v-model="mergeVotes"
            inset
            dense
            label="merge up-/downvotes"
            color="success"
            hide-details
          ></v-switch>
        </v-col>
        <v-col cols="4" class="py-0 merge-topics-details-meta">
          <div class="mt-5 mr-2 text-right grey--text text--darken-2">
            <v-icon left x-small class="mr-1 grey--text text--darken-2"
              >mdi-arrow-up-circle-outline</v-icon
            >
            {{ mergedTopic.votes.up }}
            <v-icon left x-small class="mr-1 ml-2 grey--text text--darken-2"
              >mdi-arrow-down-circle-outline</v-icon
            >
            {{ mergedTopic.votes.down }}
          </div>
        </v-col>

        <!--------------------->
        <!-- Delete original -->
        <!--------------------->

        <v-col cols="12" class="py-0">
          <v-switch
            v-model="deleteOld"
            inset
            dense
            label="delete selected topics"
            color="success"
            hide-details
          ></v-switch>
        </v-col>
      </v-row>
    </v-container>

    <v-divider></v-divider>

    <v-card-actions class="mt-3">
      <v-spacer></v-spacer>
      <v-btn
        color="awake-red-color darken-1"
        outlined
        @click="$emit('input', false)"
        class="text-lowercase"
      >
        <v-icon left class="red-icon">$awakeClose</v-icon>
        abort
      </v-btn>
      <v-btn
        color="primary"
        dark
        depressed
        @click="$emit('input', false)"
        class="text-lowercase selection-toolbar-btn"
      >
        <v-icon left>$awakeMerge</v-icon>
        merge topics
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'PopupMergeTopics',
  components: {},
  props: {
    dialog: true,
    selection: []
  },
  data: () => ({
    generateSummary: true,
    mergeDiscussion: true,
    mergeVotes: true,
    deleteOld: true,
    mergeTitle: '',
    mergeSummary: ''
  }),
  methods: {
    ...mapActions('dashboard', ['pinTopic', 'unselectAllTopics']),
    ...mapGetters('dashboard', ['getTopicById']),

    getTopicDetails (id) {
      const topic = this.getTopicById()(id)
      console.log(topic)

      return topic
    }
  },
  computed: {
    getColSize () {
      if (this.selection.length === 2) {
        return 6
      } else if (this.selection.length >= 3) {
        return 4
      } else {
        return 12
      }
    },

    mergedTopic () {
      const newTopic = {
        id: 999999,
        relevanceScore: 100,
        title: '',
        tags: [],
        ai: false,
        hot: false,
        pinned: true,
        lastActivity: null,
        excerpt: '',
        items: {
          total: 0,
          new: 0
        },
        comments: {
          total: 0,
          new: 0
        },
        votes: {
          up: 0,
          down: 0
        },
        selected: false
      }

      this.selection.forEach((id) => {
        newTopic.items.total += this.getTopicById()(id).items.total
        newTopic.items.new += this.getTopicById()(id).items.new

        newTopic.comments.total += this.mergeDiscussion
          ? this.getTopicById()(id).comments.total
          : 0
        newTopic.comments.new += this.mergeDiscussion
          ? this.getTopicById()(id).comments.new
          : 0

        newTopic.votes.up += this.mergeVotes
          ? this.getTopicById()(id).votes.up
          : 0
        newTopic.votes.down += this.mergeVotes
          ? this.getTopicById()(id).votes.down
          : 0
      })

      return newTopic
    }
  },
  mounted () {}
}
</script>
