<template>
  <v-overlay :dark="false" style="z-index: 10000">
    <v-card class="mx-auto" outlined>
      <v-card-title class="justify-center">{{ $t('assess.confirmation.confirmation_text') }}</v-card-title>
      <v-card-text class="font-weight-black">{{ title_name }}</v-card-text>
      <v-card-actions class="justify-center">
        <v-btn @click.prevent="confirmDeletion" class="red accent-1" color="red darken-4" text>
          <v-icon color="red darken-4">{{ UI.ICON.DELETE }}</v-icon>
          {{ $t('assess.confirmation.confirm') }}
        </v-btn>
        <v-btn @click.prevent="cancelDeletion" class="mx-4 justify-center"
               data-btn="delete">{{ $t('assess.confirmation.cancel') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-overlay>
</template>

<script>

export default {
  props: {
    title_name: String,
  },
  methods: {
    confirmDeletion() {
      this.$emit('confirm');
    },
    cancelDeletion() {
      this.$emit('close');
    }
  }
}
</script>

<style>
</style>
