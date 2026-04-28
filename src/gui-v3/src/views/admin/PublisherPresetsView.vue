<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.publisher_presets"
      :total-count="configStore.publisherPresets.total_count"
      total-count-title="publisher_preset.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewPublisherPreset :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.publisherPresets.items"
      card-item="CardCompact"
      delete-permission="CONFIG_PUBLISHER_PRESET_DELETE"
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
import { useConfigStore } from '@/stores/config'
import { deletePublisherPreset } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewPublisherPreset from '@/components/config/publishers/NewPublisherPreset.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadPublisherPresets(filter.value)
  } catch (error) {
    console.error('Error loading publisher presets:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (preset) => {
  try {
    await deletePublisherPreset(preset)
    console.log('Publisher preset deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting publisher preset:', error)
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
