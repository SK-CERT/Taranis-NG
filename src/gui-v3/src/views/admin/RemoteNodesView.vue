<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.remote_nodes"
      :total-count="configStore.remoteNodes.total_count"
      total-count-title="remote_node.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewRemoteNode :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.remoteNodes.items"
      card-item="CardCompact"
      delete-permission="CONFIG_REMOTE_NODE_DELETE"
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
import { deleteRemoteNode } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewRemoteNode from '@/components/config/remote/NewRemoteNode.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadRemoteNodes(filter.value)
  } catch (error) {
    console.error('Error loading remote nodes:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (node) => {
  try {
    await deleteRemoteNode(node)
    console.log('Remote node deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting remote node:', error)
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
