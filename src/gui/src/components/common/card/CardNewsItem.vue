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
        'news-item',
        'dark-grey--text',
        {
          selected: newsItem.selected,
          'corner-tag-shared': newsItem.shared && !newsItem.restricted,
          'corner-tag-restricted': newsItem.restricted,
          'status-important': newsItem.important,
          'status-unread': !newsItem.read
        }
      ]"
      @click="toggleSelection"
    >
      <div
        v-if="newsItem.shared && !newsItem.restricted"
        class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
      >
        <v-icon x-small class="flipped-icon">$awakeShare</v-icon>
      </div>

      <div
        v-if="newsItem.restricted"
        class="news-item-corner-tag text-caption text-weight-bold text-uppercase white--text"
      >
        <v-icon x-small>mdi-lock-outline</v-icon>
      </div>

      <div class="news-item-action-bar">
        <v-tooltip open-delay="1000" bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              icon
              tile
              class="news-item-topic-action"
              v-bind="attrs"
              v-on="on"
              v-if="isTopic"
              @click.native.capture="removeFromTopic($event)"
            >
              <v-icon> $newsItemActionRemove </v-icon>
            </v-btn>
          </template>
          <span>remove from topic</span>
        </v-tooltip>

        <v-tooltip open-delay="1000" bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              icon
              tile
              class="news-item-sharing-set-action"
              v-bind="attrs"
              v-on="on"
              v-if="isSharingSet"
              @click.native.capture="removeFromTopic($event)"
            >
              <v-icon> $newsItemActionRemove </v-icon>
            </v-btn>
          </template>
          <span>remove from sharing Set</span>
        </v-tooltip>

        <v-tooltip open-delay="1000" bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              v-on="on"
              icon
              tile
              class="news-item-action"
              :class="[{ active: newsItem.read }]"
              @click.native.capture="markAsRead($event)"
            >
              <v-icon> $newsItemActionRead </v-icon>
            </v-btn>
          </template>
          <span>mark as read/unread</span>
        </v-tooltip>

        <v-tooltip open-delay="1000" bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              v-on="on"
              icon
              tile
              class="news-item-action"
              :class="[{ active: newsItem.important }]"
              @click.native.capture="markAsImportant($event)"
            >
              <v-icon> $newsItemActionImportant </v-icon>
            </v-btn>
          </template>
          <span>mark as important</span>
        </v-tooltip>

        <v-dialog v-model="deleteDialog" width="600">
          <template #activator="{ on: deleteDialog }">
            <v-tooltip>
              <template #activator="{ on: tooltip }">
                <v-btn
                  v-on="{ ...tooltip, ...deleteDialog }"
                  icon
                  tile
                  class="news-item-action"
                >
                  <v-icon> $newsItemActionDelete </v-icon>
                </v-btn>
              </template>
              <span>Tooltip text</span>
            </v-tooltip>
          </template>

          <v-card>
            <v-container>
              <v-row>
                <v-col cols="12">
                  <h2
                    class="font-weight-bold dark-grey--text text-capitalize pt-3"
                  >
                    <v-icon color="awake-red-color" class="mb-1">
                      mdi-alert-octagon-outline
                    </v-icon>
                    <span class="awake-red-color--text">
                      Delete News Item:
                    </span>
                    "{{ newsItem.title }}"
                  </h2>
                  This action deletes the news item completely and it will no
                  longer appear in other topics. Would you like to continue and
                  delete the item permanently?
                </v-col>
              </v-row>
            </v-container>

            <v-divider></v-divider>

            <v-card-actions class="mt-3">
              <v-spacer></v-spacer>
              <v-btn
                color="awake-red-color darken-1"
                outlined
                @click="deleteDialog = false"
                class="text-lowercase pr-4"
              >
                <v-icon left class="red-icon">$awakeClose</v-icon>
                abort
              </v-btn>
              <v-btn
                color="primary"
                dark
                depressed
                @click="deleteNewsItem()"
                class="text-lowercase selection-toolbar-btn pr-4"
              >
                <v-icon left>mdi-check</v-icon>
                delete
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <!-- @click.native.capture="deleteNewsItem($event)" -->

        <v-tooltip open-delay="1000" bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              v-on="on"
              icon
              tile
              :class="[{ active: newsItem.decorateSource }]"
              @click.native.capture="decorateSource($event)"
            >
              <v-icon> $newsItemActionRibbon </v-icon>
            </v-btn>
          </template>
          <span>emphasise originator</span>
        </v-tooltip>
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
                    :class="[
                      'news-item-title',
                      {
                        'status-unread': !newsItem.read
                      }
                    ]"
                  >
                    <sup v-if="!newsItem.read" class="new-indicator"> * </sup>
                    {{ newsItem.title }}
                  </h2>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p
                    class="font-weight-light dark-grey--text news-item-summary mb-0"
                  >
                    {{ newsItem.summary }}
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
                  <span class="news-item-meta-topics-list text-capitalize">
                    {{ topicsList }}
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

import { mapActions, mapGetters, mapState } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagNorm
  },
  props: {
    newsItem: {}
  },
  data: () => ({
    deleteDialog: false
  }),
  computed: {
    ...mapState('newsItemsFilter', ['filter']),

    isSharingSet () {
      return (
        this.filter.scope.sharingSets.length === 1 &&
        this.filter.scope.topics.length === 0
      )
    },

    isTopic () {
      return this.filter.scope.topics.length === 1
    },

    publishedDate () {
      return moment(this.newsItem.published).format('DD/MM/YYYY hh:mm:ss')
    },
    collectedDate () {
      return moment(this.newsItem.collected).format('DD/MM/YYYY hh:mm:ss')
    },
    topicsList () {
      const topicTitles = []
      this.newsItem.topics.forEach((id) => {
        const newTopicTitle = this.getTopicTitleById()(id)
        if (topicTitles.indexOf(newTopicTitle) === -1) {
          topicTitles.push(newTopicTitle)
        }
      })

      return topicTitles.length ? topicTitles.join(', ') : '-'
    }
  },
  methods: {
    ...mapGetters('dashboard', ['getTopicById', 'getTopicTitleById']),

    ...mapActions('assess', [
      'selectNewsItem',
      'upvoteNewsItem',
      'downvoteNewsItem',
      'removeTopicFromNewsItem'
    ]),

    getTopicTitle: function (topicId) {
      return this.getTopicTitleById()(topicId)
    },
    toggleSelection: function () {
      this.newsItem.selected = !this.newsItem.selected
      this.selectNewsItem(this.newsItem.id)
    },
    removeFromTopic: function (event) {
      event.stopPropagation()
      const topicId = this.isSharingSet
        ? this.filter.scope.sharingSets[0].id
        : this.filter.scope.topics[0].id
      this.removeTopicFromNewsItem({
        newsItemId: this.newsItem.id,
        topicId: topicId
      })
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
    deleteNewsItem: function () {
      this.$emit('deleteItem', this.newsItem.id)
      this.deleteDialog = false
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
