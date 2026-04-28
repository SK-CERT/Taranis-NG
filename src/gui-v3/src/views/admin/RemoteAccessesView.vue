<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.remote_access"
      :total-count="configStore.remoteAccess.total_count"
      total-count-title="remote_access.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewRemoteAccess :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.remoteAccess.items"
      card-item="CardCompact"
      delete-permission="CONFIG_REMOTE_ACCESS_DELETE"
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
import { deleteRemoteAccess } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewRemoteAccess from '@/components/config/remote/NewRemoteAccess.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadRemoteAccesses(filter.value)
  } catch (error) {
    console.error('Error loading remote accesses:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (remoteAccess) => {
  try {
    await deleteRemoteAccess(remoteAccess)
    console.log('Remote access deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting remote access:', error)
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
