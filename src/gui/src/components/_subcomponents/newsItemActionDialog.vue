<template>
  <v-dialog v-model="dialog" width="600">
    <template #activator="{ on: dialog }">
      <v-tooltip>
        <template #activator="{ on: tooltip, attrs }">
          <v-btn
            v-on="{ ...tooltip, ...dialog }"
            v-bind="attrs"
            icon
            tile
            class="news-item-action"
            :class="[{ active: active ? active : false }, extraClass]"
          >
            <v-icon> {{ icon }} </v-icon>
          </v-btn>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
    </template>

    <slot />
  </v-dialog>
</template>

<script>
export default {
  name: 'newsItemActionDialog',
  data: () => ({
    dialog: false
  }),
  props: {
    active: Boolean,
    icon: String,
    extraClass: String,
    tooltip: String
  },
  methods: {
    modDialog (event) {
      event.stopPropagation()
      this.$emit('click', event)
    },
    close () {
      this.dialog = false
    }
  }
}
</script>
