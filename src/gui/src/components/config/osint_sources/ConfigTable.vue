<template>
<v-container fluid class="ma-5 mt-5 pa-5 pt-0">
  <v-row>
    <v-col cols="12">
      <v-btn
        color="primary"
        dark
        class="mb-2"
        @click="addItem"
        v-if="addButton"
      >
        New Item
      </v-btn>
    </v-col>
  </v-row>
  <v-row>
    <v-col cols="12">
      <v-data-table
        ref="configTable"
        :headers="headers"
        :items="items"
        :group-by="groupByItem"
        :expanded.sync="expanded"
        show-expand
        class="elevation-1"
        hide-default-footer
        @click:row="rowClick"
      >
      <template v-slot:[`group.header`]="{ items }">
        <th :colspan="headers.length" class="text-left">
          {{ items[0].collector_type }}
        </th>
      </template>
      <template v-slot:expanded-item="{ headers, item }">
        <td :colspan="headers.length">
          More info about {{ item }}
        </td>
      </template>

      <template v-slot:[`item.default`]="{ item }">
        <v-chip :color="getDefaultColor(item.default)" dark>
          {{ item.default }}
        </v-chip>
      </template>
      <template v-slot:[`item.actions`]="{ item }">
      <v-icon
        small
        class="mr-2"
        @click="editItem(item)"
      >
        mdi-pencil
      </v-icon>
      <v-icon
        small
        @click="deleteItem(item)"
      >
        mdi-delete
      </v-icon>
      </template>
      <template v-slot:no-data>
        <v-btn
          color="primary"
        >
          Reset
        </v-btn>
      </template>
      </v-data-table>
   </v-col>
  </v-row>
  <v-row>
    <v-col cols="12">
      <v-btn v-if="canUpdate" text dark type="submit" form="form_osint_group">
      <v-icon left>mdi-content-save</v-icon>
        <span>{{ $t('osint_source_group.save') }}</span>
      </v-btn>

      <v-form @submit.prevent="add" id="form_osint_group" ref="form" class="px-4">
          <v-row no-gutters>
              <v-col cols="12">
                  <v-data-table :disabled="!canUpdate"
                                v-model="selected_osint_sources"
                                :headers="headers"
                                :items="getOSINTSources"
                                item-key="id"
                                :show-select="canUpdate"
                                class="elevation-1"
                  >
                      <template v-slot:top>
                          <v-toolbar flat color="white">
                              <v-toolbar-title>{{ $t('osint_source_group.osint_sources') }}
                              </v-toolbar-title>
                          </v-toolbar>
                      </template>
                  </v-data-table>
              </v-col>
          </v-row>

          <v-row no-gutters class="pt-2">
              <v-col cols="12">
                  <v-alert v-if="show_validation_error" dense type="error" text>
                      {{ $t('osint_source_group.validation_error') }}
                  </v-alert>
                  <v-alert v-if="show_error" dense type="error" text>
                      {{ $t('osint_source_group.error') }}
                  </v-alert>
              </v-col>
          </v-row>
      </v-form>
    </v-col>
  </v-row>
</v-container>
</template>

<script>
export default {
  name: 'ConfigTable',
  emits: ['delete-item', 'edit-item', 'add-item'],
  props: {
    items: Array,
    addButton: {
      type: Boolean,
      default: false
    },
    groupByItem: {
      type: String,
      default: null
    }
  },
  data: () => ({
    selected_row: {},
    expanded: []
  }),
  computed: {
    headers () {
      var headers = (this.items.length > 0 ? Object.keys(this.items[0]).map(key => {
        return {
          text: key,
          value: key
        }
      }) : [])
      headers.push({
        text: 'Actions',
        value: 'actions',
        sortable: false
      })
      return headers
    }
  },
  methods: {
    getDefaultColor (defaultgroup) {
      return (defaultgroup ? 'green' : '')
    },
    deleteItem(item) {
      this.$emit('delete-item', item)
    },
    editItem(item) {
      this.$emit('edit-item', item)
    },
    addItem() {
      this.$emit('add-item')
    },
    rowClick(item, event) {
      this.selected_row = item
      if (event.isExpanded) {
        const index = this.expanded.findIndex(i => i === item)
        this.expanded.splice(index, 1)
      } else {
        this.expanded.push(item)
      }
    }
  }
}
</script>
