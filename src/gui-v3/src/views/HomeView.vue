<template>
  <v-container fluid fill-height>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6">
        <v-card>
          <v-card-title class="text-display-small text-center bg-gradient white--text pa-6">
            <v-icon left color="white" size="large">{{ ICONS.SHIELD_SEARCH }}</v-icon>
            Taranis NG
          </v-card-title>
          <v-card-text class="text-center pa-6">
            <v-progress-circular
              indeterminate
              color="primary"
              size="64"
              class="mb-4"
            />
            <p class="text-headline-small">Redirecting...</p>
            <p class="text-body-medium text-medium-emphasis">
              You will be redirected to your default view based on your permissions.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ICONS } from '@/config/ui-constants'

// This view is temporary - the router automatically redirects
// authenticated users to /dashboard, /config, or /myassets
// based on their permissions
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
