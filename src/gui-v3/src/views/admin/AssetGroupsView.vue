<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.asset_groups"
      :total-count="assetsStore.asset_groups.total_count"
      total-count-title="asset_group.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewAssetGroup :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="assetsStore.asset_groups.items"
      card-item="CardCompact"
      delete-permission="MY_ASSETS_CONFIG"
      :loading="loading"
      @delete="handleDelete"
      @edit="handleEdit"
      @refresh="loadData"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssetsStore } from '@/stores/assets'
import { deleteAssetGroup } from '@/api/assets'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewAssetGroup from '@/components/config/assets/NewAssetGroup.vue'

const { t } = useI18n()
const assetsStore = useAssetsStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await assetsStore.loadAssetGroups(filter.value)
  } catch (error) {
    console.error('Error loading asset groups:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (group) => {
  try {
    await deleteAssetGroup(group)
    console.log('Asset group deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting asset group:', error)
  }
}

const handleEdit = (item) => {
  editItem.value = item
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
