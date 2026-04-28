<template>
  <v-container fluid class="pa-0">
    <v-card flat>
      <v-card-text class="pa-0">
        <v-row no-gutters>
          <v-col cols="12">
            <ToolbarFilterAssets @update-filter="handleFilterUpdate">
              <template #add-button>
                <v-btn
                  v-if="canAddAssets"
                  color="success"
                  prepend-icon="mdi-plus"
                  @click="handleShowAddDialog"
                >
                  {{ $t('asset.add') }}
                </v-btn>
              </template>
            </ToolbarFilterAssets>
          </v-col>
        </v-row>

        <v-row no-gutters>
          <v-col cols="12">
            <v-alert
              v-if="!canAddAssets"
              type="info"
              variant="tonal"
              class="ma-4"
            >
              {{ $t('asset.no_groups_message') }}
            </v-alert>

            <ContentDataAssets v-else ref="contentDataRef" />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- New Asset Dialog -->
    <NewAsset ref="newAssetRef" />

    <!-- Asset Detail Dialog -->
    <AssetDetailDialog ref="assetDetailDialogRef" />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAssetsStore } from '@/stores/assets'
import { useAuthStore } from '@/stores/auth'
import ToolbarFilterAssets from '@/components/assets/ToolbarFilterAssets.vue'
import ContentDataAssets from '@/components/assets/ContentDataAssets.vue'
import NewAsset from '@/components/assets/NewAsset.vue'
import AssetDetailDialog from '@/components/assets/AssetDetailDialog.vue'

const assetsStore = useAssetsStore()
const authStore = useAuthStore()

const contentDataRef = ref(null)
const newAssetRef = ref(null)
const assetDetailDialogRef = ref(null)

const canAddAssets = computed(() => {
  const groups = assetsStore.asset_groups?.items || []
  return Array.isArray(groups) && groups.length > 0
})

function handleFilterUpdate(filter) {
  if (contentDataRef.value) {
    contentDataRef.value.updateFilter(filter)
  }
}

function handleShowAddDialog() {
  if (newAssetRef.value) {
    newAssetRef.value.openDialog()
  }
}

onMounted(async () => {
  try {
    await assetsStore.loadAssetGroups({ search: '' })
  } catch (error) {
    console.error('Error loading asset groups:', error)
  }
})
</script>
