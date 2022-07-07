<template>
  <!-- <v-tooltip open-delay="1000" bottom :disabled="!tooltip">
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        v-bind="attrs"
        v-on="on"
        icon
        tile
        class="news-item-action"
        :class="[{ active: active ? active : false }, extraClass]"
        @click.native.capture="execute($event)"
      >
        <v-icon> {{ icon }} </v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip> -->

  <v-dialog
    v-model="dialog"
    width="600">

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

    <slot/>
    
  </v-dialog>

</template>

<script>
import PopupDeleteItem from '@/components/popups/PopupDeleteItem'
export default {
  name: 'newsItemActionDialog',
  components: {
    PopupDeleteItem
  },
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
      this.$emit('input', event)
    },
    close() {
      console.log("close triggered")
      this.dialog = false
    }
  }
}
</script>
