<template>
    <v-container class="pa-0">
      <v-row>
        <v-col>

          <!-- search -->

          <v-row class="pl-5 pr-5 pt-5">
            <v-col>
              <h4>search</h4>
            </v-col>
          </v-row>
          <v-row class="pl-5 pr-5">
            <v-col>
              <v-text-field label="search" outlined dense append-icon="$awakeSearch"></v-text-field>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-0 mb-0"></v-divider>
        
      <v-row>
        <v-col>

          <!-- filter results -->
          
          <v-row class="pl-5 pr-5 pt-5">
            <v-col>
              <h4>filter results</h4>
            </v-col>
          </v-row>

          <!-- time tags -->
          <v-row class="pl-5 pr-5">
            <v-col justify="space-between" class="d-flex pb-0" style="column-gap: 10px;">
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.tags.all,}]" @click="dateSelector('all')"> all </v-btn>
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.tags.today,}]" @click="dateSelector('today')"> today </v-btn>
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.tags.week,}]" @click="dateSelector('week')"> this week </v-btn>
            </v-col>
          </v-row>

          <!-- date picker -->
          <v-row class="pl-5 pr-5 mt-0 mb-0">
            <v-col>
              <v-menu
                ref="datePicker"
                v-model="datePicker"
                :close-on-content-click="false"
                :return-value.sync="date"
                transition="scale-transition"
                offset-y
                min-width="auto"
              >
                <template v-slot:activator="{ on, attrs }">
                  <v-text-field readonly outlined dense append-icon="mdi-calendar-range-outline"
                    v-model="dateRangeText"
                    v-bind="attrs"
                    v-on="on"
                    placeholder="Date range"
                    hide-details
                  ></v-text-field>
                </template>
                <v-date-picker
                  v-model="date.range"
                  range
                  no-title
                  scrollable
                >
                  <v-spacer></v-spacer>
                  <v-btn text color="primary" @click="datePicker = false">
                    Cancel
                  </v-btn>
                  <v-btn text color="primary" @click="$refs.datePicker.save(date), dateSelector('range')">
                    OK
                  </v-btn>
                </v-date-picker>
              </v-menu>
            </v-col>
          </v-row>

          <!-- tags -->
          <v-row class="pl-5 pr-5 mt-1">
            <v-col>
              <v-combobox
              v-model="selectedTags"
              :items="tags"
              label="tags"
              multiple
              deletable-chips
              outlined 
              dense
              append-icon="mdi-chevron-down"
            >
              <template v-slot:selection="{ item, index }">
                <v-chip small close label x-small v-if="index < 1" @click:close="deleteChip(item)">
                  <span>{{ item }}</span>
                </v-chip>
                <span
                  v-if="index === 1"
                  class="grey--text text-caption"
                >
                  (+{{ selectedTags.length - 1 }} others)
                </span>
              </template>
            </v-combobox>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-0 mb-0"></v-divider>
        
      <v-row>
        <v-col>

          <v-row class="pl-5 pr-5 pt-5">
            <v-col>
              <h4>only show</h4>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-0 mb-0"></v-divider>
        
      <v-row>
        <v-col>

          <v-row class="pl-5 pr-5 pt-5">
            <v-col>
              <h4>sort by</h4>
            </v-col>
          </v-row>

        </v-col>
      </v-row>
      
    </v-container>
</template>

<script>

export default {
  name: 'DashboardNav',
  components: {

  },
  data: () => ({
    links: [],
    menu: false,
    date: {
      tags: {
        all: true,
        today: false,
        week: false
      },
      range: []
    },
    selectedTags: ['all'],
    tags: [
      'State',
      'Vulnerability',
      'Threat',
      'DDoS',
      'Cyberwar',
      'Java',
      'CVE',
    ],
  }),
    computed: {
      dateRangeText () {
        return this.date.range.join(' - ')
      },
    },
    methods: {
      deleteChip(chip) {
        this.selectedTags = this.selectedTags.filter(c => c !== chip)
      },
      dateSelector(elem) {
        this.date.tags[elem] = !this.date.tags[elem]
        if (elem === "all") {
          this.date.tags.today = false;
          this.date.tags.week = false;
          this.date.range = [];
        } else if (elem === "range") {
          this.date.tags.today = false;
          this.date.tags.week = false;
          this.date.tags.all = false;
        } else {
          this.date.tags.all = false;
        }
      }
    },
}
</script>
