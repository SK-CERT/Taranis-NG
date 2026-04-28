<template>
  <v-toolbar flat density="compact">
    <v-text-field
      v-model="filterData.search"
      prepend-inner-icon="mdi-magnify"
      :label="$t('toolbar_filter.search')"
      variant="outlined"
      density="compact"
      hide-details
      clearable
      class="mr-2"
      style="max-width: 300px"
      @update:model-value="updateFilter"
    />

    <v-chip-group class="mr-2">
      <v-chip
        :color="filterData.vulnerable ? 'error' : 'default'"
        :variant="filterData.vulnerable ? 'flat' : 'outlined'"
        @click="toggleVulnerable"
      >
        <v-icon start>mdi-shield-alert</v-icon>
        {{ $t('asset.vulnerable') }}
      </v-chip>
    </v-chip-group>

    <v-chip-group v-model="sortSelection" mandatory class="mr-2">
      <v-chip value="ALPHABETICAL" variant="outlined">
        <v-icon start>mdi-sort-alphabetical-ascending</v-icon>
        {{ $t('asset.sort.alphabetical') }}
      </v-chip>
      <v-chip value="VULNERABILITY" variant="outlined">
        <v-icon start>mdi-sort-numeric-descending</v-icon>
        {{ $t('asset.sort.vulnerability') }}
      </v-chip>
    </v-chip-group>

    <v-spacer />

    <div class="text-caption mr-4">
      {{ $t('asset.total') }}: {{ assetsStore.assets.total_count }}
    </div>

    <slot name="add-button" />
  </v-toolbar>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAssetsStore } from '@/stores/assets'

const assetsStore = useAssetsStore()

const emit = defineEmits(['update-filter'])

const filterData = ref({
  search: '',
  vulnerable: false,
  sort: 'ALPHABETICAL'
})

const sortSelection = ref('ALPHABETICAL')

watch(sortSelection, (newValue) => {
  if (newValue) {
    filterData.value.sort = newValue
    updateFilter()
  }
})

function toggleVulnerable() {
  filterData.value.vulnerable = !filterData.value.vulnerable
  updateFilter()
}

function updateFilter() {
  emit('update-filter', filterData.value)
}
</script>
