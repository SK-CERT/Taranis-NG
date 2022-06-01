<template>
  <smooth-scrollbar>
    <v-container class="pa-0">
      <!-- search -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="pb-0">
          <h4>search</h4>
        </v-col>

        <v-col cols="12">
          <v-text-field
            v-model="filter.search"
            label="search"
            outlined
            dense
            hide-details
            append-icon="$awakeSearch"
          ></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <!-- filter results -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>filter results</h4>
        </v-col>

        <!-- time tags -->
        <v-col cols="12" class="pb-0">
          <v-chip-group
            v-model="filter.date.selected"
            active-class="selected"
            class="date-filter-group d-flex"
            @change="
              filter.date.range = []
              defaultDate($event)
            "
          >
            <v-chip label outlined dark value="all">all</v-chip>
            <v-chip label outlined dark value="today">today</v-chip>
            <v-chip label outlined dark value="week">one week</v-chip>
          </v-chip-group>
        </v-col>

        <!-- date picker -->
        <v-col cols="12">
          <v-menu
            ref="datePicker"
            v-model="datePicker"
            :close-on-content-click="false"
            :return-value.sync="filter.date"
            transition="scale-transition"
            offset-y
            min-width="auto"
            @change="defaultDate($event)"
          >
            <template v-slot:activator="{ on, attrs }">
              <v-text-field
                readonly
                outlined
                dense
                append-icon="mdi-calendar-range-outline"
                v-model="dateRangeText"
                v-bind="attrs"
                v-on="on"
                placeholder="Date range"
                hide-details
                :class="[{ 'text-field-active': filter.date.range.length }]"
              ></v-text-field>
            </template>
            <v-date-picker
              v-model="filter.date.range"
              range
              no-title
              scrollable
              color="primary"
              @change="filter.date.selected = 'range'"
            >
              <v-spacer></v-spacer>
              <v-btn
                text
                outlined
                class="text-lowercase grey--text text--darken-2"
                @click="datePicker = false"
              >
                Cancel
              </v-btn>
              <v-btn
                text
                outlined
                color="primary"
                @click="$refs.datePicker.save(filter.date)"
              >
                OK
              </v-btn>
            </v-date-picker>
          </v-menu>
        </v-col>

        <!-- tags -->
        <v-col cols="10" class="pr-0">
          <v-combobox
            v-model="filter.tags.selected"
            :items="tagList"
            label="tags"
            multiple
            outlined
            dense
            append-icon="mdi-chevron-down"
            class="pl-0"
            hide-details
            hide-selected
            deletable-chips
            @change="defaultTag"
          >
            <template v-slot:selection="{ parent, item, index }">
              <v-chip
                small
                v-if="index < 1 && !parent.isMenuActive"
                @click:close="removeSelectedTag(item)"
                label
                color="grey--lighten-4"
                close
                close-icon="$newsItemActionRemove"
                class="pa-2 ml-0 mt-1"
              >
                <span>{{ item }}</span>
              </v-chip>
              <v-chip
                small
                v-else-if="parent.isMenuActive"
                @click:close="removeSelectedTag(item)"
                label
                color="grey--lighten-4"
                close
                close-icon="$newsItemActionRemove"
                class="pa-2 ml-0 mt-1"
              >
                <span>{{ item }}</span>
              </v-chip>
              <span
                v-if="index === 1 && !parent.isMenuActive"
                class="grey--text text-caption"
              >
                (+{{ filter.tags.selected.length - 1 }})
              </span>
            </template>
          </v-combobox>
        </v-col>
        <v-col cols="2" class="pl-1 d-flex tags-logic-operator">
          <v-btn
            outlined
            dark
            @click="filter.tags.andOperator = !filter.tags.andOperator"
            :class="[
              'text-lowercase',
              'px-0',
              { selected: filter.tags.andOperator }
            ]"
          >
            <span v-if="filter.tags.andOperator"> & </span>
            <span v-else> or </span>
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>only show</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-list dense class="py-0">
            <v-list-item-group
              active-class="selected"
              v-model="filter.attributes.selected"
              multiple
              class="filter-list"
            >
              <template>
                <v-list-item
                  v-for="item in filterAttributeOptions"
                  :key="item.type"
                  class="extra-dense"
                  :ripple="false"
                  :value="item.type"
                >
                  <template v-slot:default="{ active }">
                    <v-list-item-icon class="mr-2">
                      <v-icon
                        small
                        color="grey"
                        class="filter-icon mt-auto mb-auto"
                      >
                        {{ item.icon }}
                      </v-icon>
                    </v-list-item-icon>

                    <v-list-item-content class="py-1 mt-auto mb-auto">
                      {{ item.label }}
                    </v-list-item-content>

                    <v-list-item-action>
                      <v-icon
                        v-if="active"
                        small
                        class="mt-auto mb-auto dark-grey--text text--lighten-3"
                      >
                        mdi-check-bold
                      </v-icon>
                    </v-list-item-action>
                  </template>
                </v-list-item>
              </template>
            </v-list-item-group>
          </v-list>
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>sort by</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-list dense class="py-0">
            <v-list-item-group
              v-model="order.selected"
              active-class="selected"
              class="filter-list"
              mandatory
            >
              <!-- :value-comparator="sortByActivation" -->
              <template>
                <v-list-item
                  v-for="(item, index) in orderOptions"
                  :key="item.title"
                  class="extra-dense"
                  :ripple="false"
                  :value="{ type: item.type, direction: item.direction }"
                  @click.native.capture="changeDirection($event, index)"
                >
                  <template v-slot:default="{ active }">
                    <v-list-item-icon class="mr-2">
                      <v-icon
                        small
                        color="grey"
                        class="filter-icon mt-auto mb-auto"
                      >
                        {{ item.icon }}
                      </v-icon>
                    </v-list-item-icon>

                    <v-list-item-content class="py-1 mt-auto mb-auto">
                      {{ item.label }}
                    </v-list-item-content>

                    <v-list-item-action>
                      <v-icon
                        v-if="active"
                        :class="[
                          'mt-auto',
                          'mb-auto',
                          'dark-grey--text',
                          'text--lighten-3',
                          {
                            asc: item.direction === 'asc',
                            desc: item.direction === 'desc'
                          }
                        ]"
                      >
                        mdi-chevron-up
                      </v-icon>
                    </v-list-item-action>
                  </template>
                </v-list-item>
              </template>
            </v-list-item-group>
          </v-list>
        </v-col>
      </v-row>

      <v-divider class="mt-1 mb-0"></v-divider>

      <v-row class="mt-1 mr-0 px-5 pb-10">
        <v-col cols="12" class="py-0">
          <v-checkbox
            v-model="order.keepPinned"
            dense
            hide-details
            label="Pinned always on top"
          ></v-checkbox>
        </v-col>
      </v-row>
    </v-container>
  </smooth-scrollbar>
</template>

<script>
import { mapState } from 'vuex'

export default {
  name: 'DashboardNav',
  components: {},
  data: () => ({
    links: [],
    datePicker: false,
    date: {
      range: [],
      selected: 'all'
    },
    tags: {
      andOperator: true,
      selected: ['all']
    },
    filterAttributeOptions: [
      { type: 'active', label: 'active topics', icon: 'mdi-message-outline' },
      { type: 'pinned', label: 'pinned topics', icon: '$awakePin' },
      { type: 'hot', label: 'hot topics', icon: 'mdi-star-outline' },
      {
        type: 'upvoted',
        label: 'upvoted topics',
        icon: 'mdi-arrow-up-circle-outline'
      },
      {
        type: 'selected',
        label: 'selected',
        icon: 'mdi-checkbox-marked-outline'
      }
    ],
    orderOptions: [
      {
        label: 'relevance score',
        icon: 'mdi-star-outline',
        type: 'relevanceScore',
        direction: 'desc'
      },
      {
        label: 'last activity',
        icon: 'mdi-calendar-range-outline',
        type: 'lastActivity',
        direction: ''
      },
      {
        label: 'new news items',
        icon: 'mdi-file-outline',
        type: 'newItems',
        direction: ''
      },
      {
        label: 'new comments',
        icon: 'mdi-message-outline',
        type: 'newComments',
        direction: ''
      },
      {
        label: 'upvotes',
        icon: 'mdi-arrow-up-circle-outline',
        type: 'upvotes',
        direction: ''
      }
    ],
    tagList: [
      'all',
      'State',
      'Cyberwar',
      'Threat',
      'DDoS',
      'Vulnerability',
      'Java',
      'CVE',
      'OT/CPS',
      'Python',
      'Privacy',
      'Social',
      'APT',
      'MitM'
    ]
  }),
  computed: {
    ...mapState('topicsFilter', ['filter', 'order']),

    dateRangeText () {
      return this.date.range.join(' – ')
    },
    getData () {
      return this.$store.getters.getDashboardData
    }
  },
  methods: {
    defaultDate (event) {
      if (!this.filter.date.selected) {
        this.filter.date.selected = 'all'
      }
    },
    defaultSource () {
      if (!this.sources.selected.length) {
        this.sources.selected = ['all']
      } else if (this.sources.selected !== ['all']) {
        this.sources.selected = this.sources.selected.filter(
          (item) => item !== 'all'
        )
      }
    },
    defaultTag () {
      if (!this.filter.tags.selected.length) {
        this.filter.tags.selected = ['all']
      } else if (this.filter.tags.selected !== ['all']) {
        this.filter.tags.selected = this.filter.tags.selected.filter(
          (item) => item !== 'all'
        )
      }
    },
    removeSelectedTag (chip) {
      this.filter.tags.selected = this.filter.tags.selected.filter(
        (c) => c !== chip
      )
      this.defaultTag()
    },
    changeDirection (event, index) {
      event.preventDefault()
      var newDirection =
        this.orderOptions[index].direction === 'desc' ? 'asc' : 'desc'
      this.orderOptions = this.orderOptions.map((item) => ({
        ...item,
        direction: ''
      }))
      this.orderOptions[index].direction = newDirection
    }
  }
}
</script>
