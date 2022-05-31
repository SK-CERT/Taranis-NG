<template>
  <v-col cols="12" xl="6">
    <v-card
      tile
      elevation="4"
      outlined
      height="100%"
      :class="[
        'pl-5',
        'align-self-stretch',
        'newsItem',
        'dark-grey--text',
        {
          selected: newsItem.selected
        }
      ]"
      @click="toggleSelection"
    >
      <div
        class="status-bar"
        :class="[
          {
            'status-important': newsItem.important,
            'status-unread': !newsItem.read
          }
        ]"
      ></div>

      <div class="news-item-action-bar">
        <v-btn icon tile class="news-item-topic-action">
          <v-icon> $newsItemActionRemove </v-icon>
        </v-btn>
        <v-btn
          icon
          tile
          class="news-item-action"
          :class="[{ active: newsItem.read }]"
          @click.native.capture="markAsRead($event)"
        >
          <v-icon> $newsItemActionRead </v-icon>
        </v-btn>
        <v-btn
          icon
          tile
          class="news-item-action"
          :class="[{ active: newsItem.important }]"
          @click.native.capture="markAsImportant($event)"
        >
          <v-icon> $newsItemActionImportant </v-icon>
        </v-btn>
        <v-btn
          icon
          tile
          class="news-item-action"
          @click.native.capture="deleteNewsItem($event)"
        >
          <v-icon> $newsItemActionDelete </v-icon>
        </v-btn>
        <v-btn
          icon
          tile
          class="news-item-action"
          :class="[{ active: newsItem.decorateSource }]"
          @click.native.capture="decorateSource($event)"
        >
          <v-icon> $newsItemActionRibbon </v-icon>
        </v-btn>
      </div>

      <v-container no-gutters class="ma-0 pa-0">
        <v-row no-gutters>
          <v-col
            cols="12"
            sm="12"
            md="7"
            class="d-flex flex-column"
            align-self="start"
          >
            <v-container column style="height: 100%">
              <v-row class="flex-grow-0 mt-0">
                <v-col class="pb-1">
                  <h2
                    class="headline dark-grey--text text-capitalize news-item-headline"
                  >
                    {{ newsItem.title }}
                  </h2>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p
                    class="font-weight-light dark-grey--text news-item-excerpt mb-0"
                  >
                    {{ newsItem.excerpt }}
                  </p>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-1">
                <v-col
                  cols="12"
                  class="mx-0 d-flex justify-start flex-wrap py-1"
                >
                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeEye</v-icon>
                    view details
                  </v-btn>

                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeReport</v-icon>
                    create report
                  </v-btn>
                  <v-btn
                    outlined
                    class="text-lowercase news-item-btn mr-1 mt-1"
                    @click.native.capture="viewTopic($event)"
                  >
                    <v-icon left>$awakeRelated</v-icon>
                    show related items
                  </v-btn>
                  <div class="d-flex align-start justify-center mr-3 ml-2 mt-1">
                    <v-icon
                      left
                      small
                      color="awake-green-color"
                      class="align-self-center mr-1"
                      @click.native.capture="upvote($event)"
                      >mdi-arrow-up-circle-outline</v-icon
                    >
                    <span
                      class="text-caption font-weight-light dark-grey--text align-self-center"
                      >{{ newsItem.votes.up }}</span
                    >
                  </div>
                  <div class="d-flex align-start justify-center mr-3 mt-1">
                    <v-icon
                      left
                      small
                      color="awake-red-color"
                      class="align-self-center mr-1"
                      @click.native.capture="downvote($event)"
                      >mdi-arrow-down-circle-outline</v-icon
                    >
                    <span
                      class="text-caption font-weight-light dark-grey--text align-self-center"
                      >{{ newsItem.votes.down }}</span
                    >
                  </div>
                </v-col>
              </v-row>
            </v-container>
          </v-col>

          <v-divider vertical class="d-none d-sm-flex"></v-divider>
          <v-divider class="d-flex d-sm-none"></v-divider>

          <v-col
            cols="12"
            sm="12"
            md="5"
            class="d-flex flex-column"
            align-self="start"
            style="height: 100%"
          >
            <v-container column style="height: 100%">
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Published:</strong>
                </v-col>
                <v-col>
                  {{ publishedDate }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Collected:</strong>
                </v-col>
                <v-col>
                  {{ collectedDate }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Source:</strong>
                </v-col>
                <v-col>
                  {{ newsItem.source.domain }} <br />
                  <a
                    :href="newsItem.source.url"
                    target="_blank"
                    icon
                    class="meta-link d-flex"
                  >
                    <v-icon left x-small class="mr-1">mdi-open-in-new</v-icon>
                    <span class="label">{{ newsItem.source.url }}</span>
                  </a>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Source Type:</strong>
                </v-col>
                <v-col>
                  {{ newsItem.source.type }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Added by:</strong>
                </v-col>
                <v-col>
                  <span :class="[{ decorateSource: newsItem.decorateSource }]">
                    {{ newsItem.addedBy }}
                    <v-icon
                      right
                      small
                      v-if="newsItem.decorateSource"
                      class="ml-0"
                      >$awakeRibbon</v-icon
                    >
                  </span>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Topics:</strong>
                </v-col>
                <v-col>
                  <span
                    v-for="(topic, index) in newsItem.topics"
                    :key="topic"
                    class="text-capitalize"
                    >{{ topic }}
                    <span
                      v-if="index != Object.keys(newsItem.topics).length - 1"
                      >,
                    </span>
                  </span>
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label d-flex align-center">
                  <strong>Tags:</strong>
                </v-col>
                <v-col>
                  <tag-norm
                    v-for="tag in newsItem.tags"
                    :key="tag.label"
                    :tag="tag"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
  </v-col>
</template>

<script>
import TagNorm from '@/components/common/tags/TagNorm'
import moment from 'moment'

import { mapActions } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagNorm
  },
  props: {
    newsItem: {}
  },
  data: () => ({}),
  computed: {
    publishedDate () {
      return moment(this.newsItem.published).format('DD/MM/YYYY hh:mm:ss')
    },
    collectedDate () {
      return moment(this.newsItem.collected).format('DD/MM/YYYY hh:mm:ss')
    }
  },
  methods: {
    ...mapActions('assess', [
      'selectNewsItem',
      'upvoteNewsItem',
      'downvoteNewsItem'
    ]),

    toggleSelection: function () {
      this.newsItem.selected = !this.newsItem.selected
      this.selectNewsItem(this.newsItem.id)
      // this.$emit('selectItem', this.newsItem.id)
    },
    markAsRead: function (event) {
      event.stopPropagation()
      this.newsItem.read = !this.newsItem.read
    },
    markAsImportant: function (event) {
      event.stopPropagation()
      this.newsItem.important = !this.newsItem.important
    },
    decorateSource: function (event) {
      event.stopPropagation()
      this.newsItem.decorateSource = !this.newsItem.decorateSource
    },
    deleteNewsItem: function (event) {
      event.stopPropagation()
      this.$emit('deleteItem', this.newsItem.id)
    },
    upvote: function (event) {
      event.stopPropagation()
      this.upvoteNewsItem(this.newsItem.id)
    },
    downvote: function (event) {
      event.stopPropagation()
      this.downvoteNewsItem(this.newsItem.id)
    },
    viewTopic: function (event) {
      event.stopPropagation()
      console.log('view Topics clicked')
    }
  }
}
</script>
