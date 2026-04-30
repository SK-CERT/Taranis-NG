<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.osint_source_groups"
      :total-count="configStore.osintSourceGroups.total_count"
      total-count-title="osint_source_group.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewOSINTSourceGroup :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.osintSourceGroups.items"
      card-item="CardCompact"
      delete-permission="CONFIG_OSINT_SOURCE_GROUP_DELETE"
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
import { deleteOSINTSourceGroup } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewOSINTSourceGroup from '@/components/config/osint-sources/NewOSINTSourceGroup.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadOSINTSourceGroups(filter.value)
  } catch (error) {
    console.error('Error loading OSINT source groups:', error)
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
    await deleteOSINTSourceGroup(group)
    console.log('OSINT source group deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting OSINT source group:', error)
  }
}

const handleEdit = (group) => {
  editItem.value = group
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
