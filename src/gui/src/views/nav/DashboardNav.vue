<template>
  <v-container class="pa-0">
    <!-- search -->
    <v-row class="my-4 mr-0 px-5">
      <v-col cols="12" class="pb-0">
        <h4>search</h4>
      </v-col>

      <v-col cols="12">
        <v-text-field
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
    <v-row class="my-4 mr-0 px-5">
      <v-col cols="12" class="py-0">
        <h4>filter results</h4>
      </v-col>

      <!-- time tags -->
      <v-col cols="12" class="pb-0">
        <v-chip-group
          v-model="date.selected"
          active-class="selected"
          class="date-filter-group d-flex"
          @change="
            date.range = [];
            defaultDate($event);
          "
        >
          <v-chip label outlined dark value="all">all</v-chip>
          <v-chip label outlined dark value="today">today</v-chip>
          <v-chip label outlined dark value="week">this week</v-chip>
        </v-chip-group>
      </v-col>

      <!-- date picker -->
      <v-col cols="12">
        <v-menu
          ref="datePicker"
          v-model="datePicker"
          :close-on-content-click="false"
          :return-value.sync="date"
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
              :class="[{ 'text-field-active': date.range.length }]"
            ></v-text-field>
          </template>
          <v-date-picker
            v-model="date.range"
            range
            no-title
            scrollable
            color="primary"
            @change="date.selected = 'range'"
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
              @click="$refs.datePicker.save(date)"
            >
              OK
            </v-btn>
          </v-date-picker>
        </v-menu>
      </v-col>

      <!-- tags -->
      <v-col cols="10" class="pr-0">
        <v-combobox
          v-model="tags.selected"
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
            <v-chip small v-if="index < 1 && !parent.isMenuActive" @click:close="removeSelectedTag(item)" label color="grey--lighten-4"
            close close-icon="$newsItemActionRemove" class="pa-2 ml-0 mt-1">
              <span>{{ item }}</span>
            </v-chip>
            <v-chip small v-else-if="parent.isMenuActive" @click:close="removeSelectedTag(item)" label color="grey--lighten-4"
            close close-icon="$newsItemActionRemove" class="pa-2 ml-0 mt-1">
              <span>{{ item }}</span>
            </v-chip>
            <span
              v-if="index === 1 && !parent.isMenuActive"
              class="grey--text text-caption"
            >
              (+{{ tags.selected.length - 1 }})
            </span>
          </template>
        </v-combobox>
      </v-col>
      <v-col cols="2" class="pl-1 d-flex tags-logic-operator">
        <v-btn
          outlined
          dark
          @click="tags.andOperator = !tags.andOperator"
          :class="['text-lowercase', 'px-0', { selected: tags.andOperator }]"
        >
          <span v-if="tags.andOperator"> & </span>
          <span v-else> or </span>
        </v-btn>
      </v-col>
    </v-row>

    <v-divider class="mt-0 mb-0"></v-divider>

    <v-row class="my-4 mr-0 px-5">
      <v-col cols="12" class="py-0">
        <h4>only show</h4>
      </v-col>

      <v-col cols="12" class="pt-2">
        <v-list dense class="py-0">
          <v-list-item-group
            v-model="filterBy.selected"
            active-class="selected"
            multiple
            class="filter-list"
          >
            <template>
              <v-list-item
                v-for="item in filterBy.list"
                :key="item.label"
                class="extra-dense"
                :ripple="false"
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

    <v-row class="my-4 mr-0 px-5">
      <v-col cols="12" class="py-0">
        <h4>sort by</h4>
      </v-col>

      <v-col cols="12" class="pt-2">
        <v-list dense class="py-0">
          <v-list-item-group
            v-model="sortBy.selected"
            active-class="selected"
            class="filter-list"
            mandatory
          >
            <!-- :value-comparator="sortByActivation" -->
            <template>
              <v-list-item
                v-for="(item, index) in sortBy.list"
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
                          desc: item.direction === 'desc',
                        },
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

    <v-row class="mt-1 mr-0 px-5">
      <v-col cols="12" class="py-0">
        <v-checkbox
          v-model="sortBy.keepPinned"
          dense
          hide-details
          label="Pinned always on top"
        ></v-checkbox>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
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
    filterBy: {
      selected: [],
      list: [
        { label: 'active topics', icon: 'mdi-message-outline' },
        { label: 'pinned topics', icon: '$awakePin' },
        { label: 'hot topics', icon: 'mdi-star-outline' },
        { label: 'upvoted topics', icon: 'mdi-arrow-up-circle-outline' }
      ]
    },
    sortBy: {
      keepPinned: true,
      selected: {},
      list: [
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
      ]
    },
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
    dateRangeText () {
      return this.date.range.join(' – ')
    },
    getData () {
      return this.$store.getters.getDashboardData
    }
  },
  methods: {
    defaultDate (event) {
      if (!this.date.selected) {
        this.date.selected = 'all'
      }
    },
    defaultTag () {
      if (!this.tags.selected.length) {
        this.tags.selected = ['all']
      } else if (this.tags.selected !== ['all']) {
        this.tags.selected = this.tags.selected.filter((item) => item !== 'all')
      }
    },
    removeSelectedTag (chip) {
      this.tags.selected = this.tags.selected.filter((c) => c !== chip)
      this.defaultTag()
    },
    changeDirection (event, index) {
      event.preventDefault()
      var newDirection =
        this.sortBy.list[index].direction === 'desc' ? 'asc' : 'desc'
      this.sortBy.list = this.sortBy.list.map((item) => ({
        ...item,
        direction: ''
      }))
      this.sortBy.list[index].direction = newDirection
    }
  },
  watch: {
    filterBy: {
      handler () {
        this.$store.dispatch('filterTopics', this.filterBy)
        // this.updateFilterList()
      },
      deep: true
    },
    sortBy: {
      handler () {
        this.$store.dispatch('sortTopics', this.sortBy)
      },
      deep: true
    },
    tags: {
      handler () {
        this.$store.dispatch('filterTopicsByTags', this.tags)
      },
      deep: true
    }
  }
}
</script>
