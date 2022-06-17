<template>
  <v-card>
    <v-form ref="form" v-model="valid">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h2
              class="font-weight-bold headline dark-grey--text text-capitalize pt-3"
            >
              Edit Topic
            </h2>
          </v-col>
        </v-row>
        <v-row>
          <!----------->
          <!-- Title -->
          <!----------->

          <v-col class="py-2">
            <v-text-field
              hide-details
              dense
              label="Title"
              outlined
              required
              v-model="newTitle"
            ></v-text-field>
          </v-col>
        </v-row>
        <v-row>
          <!------------->
          <!-- Summary -->
          <!------------->

          <v-col cols="12" class="py-0 pt-2">
            <v-textarea
              v-model="newSummary"
              label="Summary"
              hide-details
              outlined
            ></v-textarea>
          </v-col>
        </v-row>
      </v-container>

      <v-divider></v-divider>

      <v-card-actions class="mt-3">
        <v-spacer></v-spacer>
        <v-btn
          color="awake-red-color darken-1"
          outlined
          @click="$emit('input', false)"
          class="text-lowercase pr-4"
        >
          <v-icon left class="red-icon">$awakeClose</v-icon>
          abort
        </v-btn>
        <v-btn
          color="primary"
          dark
          depressed
          @click="submit()"
          class="text-lowercase selection-toolbar-btn pr-4"
        >
          <v-icon left>mdi-check</v-icon>
          apply
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'PopupEditTopic',
  components: {},
  props: {
    dialog: true,
    topic: {}
  },
  data: () => ({
    valid: true,
    newTitle: '',
    newSummary: ''
  }),
  methods: {
    ...mapActions('dashboard', ['updateTopic']),

    submit () {
      const updatedTopic = this.topic
      updatedTopic.title = this.newTitle
      updatedTopic.summary = this.newSummary
      this.updateTopic(updatedTopic)

      // Close Popup
      this.$emit('input', false)
    }
  },
  computed: {},
  mounted () {
    this.newTitle = this.topic.title
    this.newSummary = this.topic.summary
  }
}
</script>
