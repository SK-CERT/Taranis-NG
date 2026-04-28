<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.presenters_nodes"
      :total-count="configStore.presentersNodes.total_count"
      total-count-title="presenters_node.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewPresentersNode :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.presentersNodes.items"
      card-item="CardCompact"
      delete-permission="CONFIG_PRESENTERS_NODE_DELETE"
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
import { deletePresentersNode } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewPresentersNode from '@/components/config/presenters/NewPresentersNode.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadPresentersNodes(filter.value)
  } catch (error) {
    console.error('Error loading presenters nodes:', error)
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
    await deletePresentersNode(node)
    console.log('Presenters node deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting presenters node:', error)
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
