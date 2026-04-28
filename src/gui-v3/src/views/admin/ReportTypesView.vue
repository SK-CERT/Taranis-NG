<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.report_types"
      :total-count="configStore.reportItemTypesConfig.total_count"
      total-count-title="report_type.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewReportType :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.reportItemTypesConfig.items"
      card-item="CardCompact"
      delete-permission="CONFIG_REPORT_TYPE_DELETE"
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
import { deleteReportItemType } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewReportType from '@/components/config/report-types/NewReportType.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadReportItemTypesConfig(filter.value)
  } catch (error) {
    console.error('Error loading report types:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (reportType) => {
  try {
    await deleteReportItemType(reportType)
    console.log('Report type deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting report type:', error)
  }
}

const handleEdit = (reportType) => {
  editItem.value = reportType
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
