<template>
  <v-container class="mx-3 pa-5 pb-0">
    <v-row class="card-padding my-4" no-gutters>
      <v-col class="headline card-alignment mb-4" cols="12" sm="12" md="7">
        <h1 class="pl-3 text-capitalize">{{ topic.title }}</h1>
      </v-col>
    </v-row>
    <v-row class="card-padding mt-5" no-gutters>
      <v-col cols="12" sm="12" md="7" class="pr-5 card-alignment">
        <v-container column class="pt-0" style="height: 100%">
          <v-row no-gutters style="height: 100%">
            <v-col class="d-flex flex-column pt-2" style="height: 100%">
              <v-row class="flex-grow-0">
                <v-col
                  cols="12"
                  class="mx-0 px-0 d-flex justify-start flex-wrap pt-1 pb-4"
                >
                  <p class="topic-excerpt">
                    {{ topic.summary }}
                  </p>
                </v-col>
              </v-row>

              <v-spacer></v-spacer>

              <v-row
                no-gutter
                wrap
                align="center"
                justify="end"
                class="flex-grow-0 mt-0"
              >
                <v-col
                  cols="12"
                  class="mx-0 px-0 d-flex justify-start flex-wrap py-1"
                >
                  <v-btn
                    depressed
                    class="text-lowercase topic-header-btn mr-2 mt-1"
                  >
                    <v-icon left>$awakeEdit</v-icon>
                    edit
                  </v-btn>

                  <v-btn
                    depressed
                    class="text-lowercase topic-header-btn mr-2 mt-1"
                  >
                    <v-icon left>mdi-message-outline</v-icon>
                    comments
                  </v-btn>
                </v-col>
              </v-row>
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
        <v-container column class="py-0" style="height: 100%">
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Last activity:</strong>
            </v-col>
            <v-col> {{ lastActivity }} </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Total/new items:</strong>
            </v-col>
            <v-col>
              <v-icon left small>mdi-file-outline</v-icon>
              {{ topic.items.total }} / <strong>{{ topic.items.new }}</strong>
            </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Topic upvotes:</strong>
            </v-col>
            <v-col>
              <v-icon left small color="awake-green-color"
                >mdi-arrow-up-circle-outline</v-icon
              >
              {{ topic.votes.up }}
            </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Topic downvotes:</strong>
            </v-col>
            <v-col>
              <v-icon left small color="awake-red-color"
                >mdi-arrow-down-circle-outline</v-icon
              >{{ topic.votes.down }}
            </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Originator:</strong>
            </v-col>
            <v-col>
              <tag-mini label="AI" v-if="topic.ai" />
              <span v-else>{{ topic.originator }}</span>
            </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label">
              <strong>Comments:</strong>
            </v-col>
            <v-col>
              <v-icon left small>mdi-message-outline</v-icon>
              {{ topic.comments.total }} /
              <strong>{{ topic.comments.new }}</strong>
            </v-col>
          </v-row>
          <v-row class="topic-header-meta-infos">
            <v-col class="topic-header-meta-infos-label d-flex align-center">
              <strong>Tags:</strong>
            </v-col>
            <v-col>
              <tag-norm v-for="tag in topic.tags" :key="tag.label" :tag="tag" />
            </v-col>
          </v-row>
        </v-container>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { faker } from '@faker-js/faker'
import moment from 'moment'

import TagMini from '@/components/common/tags/TagMini'
import TagNorm from '@/components/common/tags/TagNorm'

// import { mapState } from 'vuex'

export default {
  name: 'TopicHeaderAssess',
  components: {
    TagMini,
    TagNorm
  },
  props: {},
  data: () => ({
    topic: {}
  }),
  methods: {},
  computed: {
    lastActivity () {
      return moment(this.topic.lastActivity).format('DD/MM/YYYY hh:mm:ss')
    }
  },
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

    this.topic = {
      id: 0,
      relevanceScore: faker.commerce.price(0, 100, 0),
      title: faker.lorem.words(Math.floor(Math.random() * (5 - 2 + 1)) + 2),
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      ai: Math.random() < 0.5,
      originator: `${faker.name.firstName()} ${faker.name.lastName()}`,
      hot: Math.random() < 0.2,
      pinned: Math.random() < 0.05,
      lastActivity: new Date(String(faker.date.recent(10))),
      summary: faker.lorem.paragraph(35),
      items: {
        total: faker.commerce.price(70, 200, 0),
        new: faker.commerce.price(0, 70, 0)
      },
      comments: {
        total: faker.commerce.price(70, 200, 0),
        new: faker.commerce.price(0, 70, 0)
      },
      votes: {
        up: faker.commerce.price(0, 150, 0),
        down: faker.commerce.price(0, 250, 0)
      },
      selected: false
    }
  }
}
</script>
