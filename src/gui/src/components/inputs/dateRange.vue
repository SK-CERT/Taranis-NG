<template>
  <v-menu
    ref="datePicker"
    :value="value"
    :return-value.sync="dateValue"
    :close-on-content-click="false"
    transition="scale-transition"
    offset-y
    min-width="auto"
    @change="defaultDate($event)"
  >
    <!-- formatted display in textfield -->
    <template v-slot:activator="{ on, attrs }">
      <v-text-field
        readonly
        outlined
        dense
        append-icon="mdi-calendar-range-outline"
        v-model="formattedDateRange"
        v-bind="attrs"
        v-on="on"
        placeholder="Date range"
        hide-details
        :class="[{ 'text-field-active': dateValue.range.length }]"
      ></v-text-field>
    </template>

    <!-- datepicker -->
    <v-date-picker
      v-model="dateValue.range"
      range
      no-title
      scrollable
      color="primary"
      @change="dateValue.selected = 'range'"
    >
      <v-spacer></v-spacer>

      <!-- Buttons -->
      <v-btn
        text
        outlined
        class="text-lowercase grey--text text--darken-2"
        @click="dateValue.range = []"
      >
        Cancel
      </v-btn>

      <v-btn
        text
        outlined
        color="primary"
        @click="$refs.datePicker.save(dateValue)"
      >
        OK
      </v-btn>
    </v-date-picker>
  </v-menu>
</template>

<script>
export default {
  name: 'dateRange',
  props: {
    value: Boolean,
    dateValue: {}
  },
  computed: {
    formattedDateRange () {
      return this.dateValue.range.join(' – ')
    }
  }
}
</script>
