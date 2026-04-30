<template>
  <v-container fluid>
    <v-row v-if="loading" justify="center">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="64" />
      </v-col>
    </v-row>

    <v-row v-else-if="!loading && assets.length === 0">
      <v-col cols="12">
        <v-alert type="info" variant="tonal">
          {{ $t('asset.no_data') }}
        </v-alert>
      </v-col>
    </v-row>

    <v-row v-else>
      <v-col
        v-for="asset in assets"
        :key="asset.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <CardAsset :asset="asset" @delete-asset="handleDeleteAsset" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAssetsStore } from '@/stores/assets'
import { deleteAsset } from '@/api/assets'
import CardAsset from '@/components/assets/CardAsset.vue'

const route = useRoute()
const assetsStore = useAssetsStore()

const loading = ref(false)
const filter = ref({
  search: '',
  vulnerable: false,
  sort: 'ALPHABETICAL'
})

const groupId = computed(() => route.params.groupId || 'all')
const assets = computed(() => {
  const items = assetsStore.assets?.items || []
  return Array.isArray(items) ? items : []
})

async function loadAssets() {
  loading.value = true
  try {
    await assetsStore.loadAssets({
      group_id: groupId.value,
      filter: filter.value
    })
  } catch (error) {
    console.error('Error loading assets:', error)
  } finally {
    loading.value = false
  }
}

async function handleDeleteAsset(asset) {
  try {
    await deleteAsset(asset)
    await loadAssets()
  } catch (error) {
    console.error('Error deleting asset:', error)
  }
}

function updateFilter(newFilter) {
  filter.value = { ...filter.value, ...newFilter }
  loadAssets()
}

watch(
  () => route.params.groupId,
  () => {
    loadAssets()
  }
)

onMounted(() => {
  loadAssets()
})

defineExpose({
  updateFilter
})
</script>
