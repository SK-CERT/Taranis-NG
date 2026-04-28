<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.osint_sources"
      :total-count="configStore.osintSources.total_count"
      total-count-title="osint_source.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewOSINTSource :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.osintSources.items"
      card-item="CardCompact"
      delete-permission="CONFIG_OSINT_SOURCE_DELETE"
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
import { deleteOSINTSource } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewOSINTSource from '@/components/config/osint-sources/NewOSINTSource.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadOSINTSources(filter.value)
  } catch (error) {
    console.error('Error loading OSINT sources:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (source) => {
  try {
    await deleteOSINTSource(source)
    console.log('OSINT source deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting OSINT source:', error)
  }
}

const handleEdit = (source) => {
  editItem.value = source
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
