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
          selected: selected,
          'corner-tag-shared': newsItem.shared && !newsItem.restricted,
          'corner-tag-restricted': newsItem.restricted,
          'status-important': newsItem.important,
          'status-unread': !newsItem.read,
        },
      ]"
      @click="toggleSelection"
    >
      <div
        v-if="newsItem.shared && !newsItem.restricted"
        class="
          news-item-corner-tag
          text-caption text-weight-bold text-uppercase
          white--text
        "
      >
        <v-icon x-small class="flipped-icon">$awakeShare</v-icon>
      </div>

      <div
        v-if="newsItem.restricted"
        class="
          news-item-corner-tag
          text-caption text-weight-bold text-uppercase
          white--text
        "
      >
        <v-icon x-small>mdi-lock-outline</v-icon>
      </div>

      <!-- Topic Actions -->

      <div class="news-item-action-bar">
        <news-item-action-dialog
          icon="$newsItemActionRemove"
          tooltip="remove item"
          ref="deleteDialog"
        >
          <popup-delete-item
            :newsItem="newsItem"
            @deleteItem="deleteNewsItem()"
            @removeFromTopic="removeFromTopic()"
            @close="$refs.deleteDialog.close()"
          />
        </news-item-action-dialog>

        <news-item-action
          :active="newsItem.read"
          icon="$newsItemActionRead"
          @click="markAsRead()"
          tooltip="mark as read/unread"
        />

        <news-item-action
          :active="newsItem.important"
          icon="$newsItemActionImportant"
          @click="markAsImportant()"
          tooltip="mark as important"
        />

        <news-item-action
          :active="newsItem.decorateSource"
          icon="$newsItemActionRibbon"
          @click="decorateSource()"
          tooltip="emphasise originator"
        />
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
                  <item-title :title="newsItem.title" :read="newsItem.read" />
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-0">
                <v-col>
                  <p class="news-item-summary">
                    {{ newsItem.summary }}
                  </p>
                </v-col>
              </v-row>

              <v-row class="flex-grow-0 mt-1">
                <v-col
                  cols="12"
                  class="mx-0 d-flex justify-start flex-wrap py-1"
                >
                  <button-outlined
                    label="view details"
                    icon="$awakeEye"
                    extraClass="mr-1 mt-1"
                    @click="viewDetails($event)"
                  />
                  <button-outlined
                    label="create report"
                    icon="$awakeReport"
                    extraClass="mr-1 mt-1"
                    @click="createReport($event)"
                  />
                  <button-outlined
                    label="show related items"
                    icon="$awakeRelated"
                    extraClass="mr-1 mt-1"
                    @click="showRelated($event)"
                  />

                  <div class="d-flex align-start justify-center mr-3 ml-2 mt-1">
                    <votes
                      :count="newsItem.votes.up"
                      type="up"
                      @input="upvote($event)"
                    />
                  </div>
                  <div class="d-flex align-start justify-center mr-3 mt-1">
                    <votes
                      :count="newsItem.votes.down"
                      type="down"
                      @input="downvote($event)"
                    />
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
            v-if="metaData"
          >
            <v-container column style="height: 100%" class="pb-5">
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Published:</strong>
                </v-col>
                <v-col>
                  {{ metaData.publishedDate }}
                </v-col>
              </v-row>
              <v-row class="news-item-meta-infos">
                <v-col class="news-item-meta-infos-label">
                  <strong>Collected:</strong>
                </v-col>
                <v-col>
                  {{ metaData.collectedDate }}
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
                    <v-icon left x-small color="primary" class="mr-1"
                      >mdi-open-in-new</v-icon
                    >
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
                    {{ metaData.addedBy }}
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
                    {{ metaData.topicsList }}
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
import newsItemAction from '@/components/inputs/newsItemAction'
import newsItemActionDialog from '@/components/inputs/newsItemActionDialog'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
import buttonOutlined from '@/components/inputs/buttonOutlined'
import itemTitle from '@/components/inputs/itemTitle'
import votes from '@/components/inputs/votes'

import { mapGetters } from 'vuex'

export default {
  name: 'CardNewsItem',
  components: {
    TagNorm,
    newsItemAction,
    newsItemActionDialog,
    PopupDeleteItem,
    buttonOutlined,
    itemTitle,
    votes
  },
  props: {
    newsItem: {},
    topicsList: [],
    topicView: Boolean,
    sharingSetView: Boolean,
    selected: Boolean
  },
  data: () => ({
    metaData: null
  }),
  methods: {
    ...mapGetters('users', ['getUsernameById']),

    toggleSelection () {
      this.$emit('selectItem', this.newsItem.id)
    },
    markAsRead () {
      this.newsItem.read = !this.newsItem.read
    },
    markAsImportant () {
      this.newsItem.important = !this.newsItem.important
    },
    decorateSource () {
      this.newsItem.decorateSource = !this.newsItem.decorateSource
    },
    removeFromTopic () {
      this.$emit('removeFromTopic', this.newsItem.id)
    },
    deleteNewsItem () {
      this.$emit('deleteItem', this.newsItem.id)
    },
    upvote (event) {
      this.$emit('upvoteItem', this.newsItem.id)
    },
    downvote (event) {
      this.$emit('downvoteItem', this.newsItem.id)
    },

    viewDetails (event) {
      console.log('not yet implemented')
    },
    createReport (event) {
      console.log('not yet implemented')
    },
    showRelated (event) {
      console.log('not yet implemented')
    },

    getMetaDate () {
      this.metaData = {
        addedBy: this.getUsernameById()(this.newsItem.addedBy),
        publishedDate: moment(this.newsItem.published).format(
          'DD/MM/YYYY hh:mm:ss'
        ),
        collectedDate: moment(this.newsItem.collected).format(
          'DD/MM/YYYY hh:mm:ss'
        ),
        topicsList: this.getTopicsList()
      }
    },
    getTopicsList () {
      const topicTitles = []
      this.newsItem.topics.forEach((id) => {
        const newTopicTitle = this.topicsList.find(
          (topic) => topic.id === id
        ).title
        if (topicTitles.indexOf(newTopicTitle) === -1) {
          topicTitles.push(newTopicTitle)
        }
      })

      return topicTitles.length ? topicTitles.join(', ') : '-'
    }
  },
  updated () {
    // console.log('card rendered!')
  },
  mounted () {
    this.$emit('init')
    this.getMetaDate()
  }
  // beforeCreate () {
  //   console.log("starting")
  // }
}
</script>
