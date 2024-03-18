<template>
  <v-overlay :dark="false" style="z-index: 10000">
    <v-card class="delete-confirm-popup">
      <v-card-title>{{ $t('assess.confirmation.confirmation_text') }}</v-card-title>
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
.delete-confirm-popup {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: white;
  padding: 20px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
  z-index: 100;
}

</style>
