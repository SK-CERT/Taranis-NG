<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.publishers_nodes"
      :total-count="configStore.publishersNodes.total_count"
      total-count-title="publishers_node.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewPublishersNode :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.publishersNodes.items"
      card-item="CardCompact"
      delete-permission="CONFIG_PUBLISHERS_NODE_DELETE"
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
import { deletePublishersNode } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewPublishersNode from '@/components/config/publishers/NewPublishersNode.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadPublishersNodes(filter.value)
  } catch (error) {
    console.error('Error loading publishers nodes:', error)
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
    await deletePublishersNode(node)
    console.log('Publishers node deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting publishers node:', error)
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
