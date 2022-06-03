<template>
  <v-app-bar
    app
    clipped
    bottom
    flat
    dense
    dark
    style="
      bottom: 0px !important;
      top: auto !important;
      height: auto !important;
    "
    color="primary"
    class="selection-toolbar"
  >
    <v-container class="py-1">
      <v-row>
        <v-col class="py-0">
          <v-btn
            v-for="button in actionButtons"
            :key="button.label"
            :ripple="false"
            text
            class="text-lowercase selection-toolbar-btn mr-1 mt-1"
          >
            <v-icon left>{{ button.icon }}</v-icon>
            {{ button.label }}
          </v-btn>
        </v-col>

        <!-- <v-spacer></v-spacer> -->

        <v-col
          cols="1"
          class="py-1 d-flex justify-content-center"
          style="min-width: fit-content"
        >
          <span class="mr-2 my-auto selection-indicator">
            selected: <strong>{{ selection.length }}</strong>
          </span>
        </v-col>
      </v-row>
    </v-container>
  </v-app-bar>
</template>

<script>
// import { mapState } from 'vuex'

export default {
  name: 'AssessSelectionToolbar',
  components: {},
  props: {
    selection: []
  },
  data: () => ({
    actionButtons: [
      {
        label: 'append to topic',
        icon: 'mdi-folder-open-outline'
      },
      {
        label: 'create topic',
        icon: 'mdi-folder-plus-outline'
      },
      {
        label: 'create sharing set',
        icon: '$awakeShareOutline'
      },
      {
        label: 'create report',
        icon: '$awakeReport'
      },
      {
        label: 'remove from topic',
        icon: '$awakeClose'
      },
      {
        label: 'delete items',
        icon: '$awakeDelete'
      }
    ]
  }),
  methods: {},
  computed: {},
  mounted () {}
}
</script>
