<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.attributes"
      :total-count="configStore.attributes.total_count"
      total-count-title="attribute.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewAttribute :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.attributes.items"
      card-item="CardCompact"
      delete-permission="CONFIG_ATTRIBUTE_DELETE"
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
import { deleteAttribute } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewAttribute from '@/components/config/attributes/NewAttribute.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadAttributes(filter.value)
  } catch (error) {
    console.error('Error loading attributes:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (attribute) => {
  try {
    await deleteAttribute(attribute)
    console.log('Attribute deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting attribute:', error)
  }
}

const handleEdit = (attribute) => {
  editItem.value = attribute
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
