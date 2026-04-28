<template>
  <v-container>
    <v-card>
      <v-card-title class="text-headline-medium">
        <v-icon start>{{ ICONS.COG }}</v-icon>
        {{ $t('nav_menu.configuration') }}
      </v-card-title>
      <v-card-text>
        <p>{{ $t('config.select_from_menu') }}</p>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ICONS } from '@/config/ui-constants'

// Configuration landing page
</script>
