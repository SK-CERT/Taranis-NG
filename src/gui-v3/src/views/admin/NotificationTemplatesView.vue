<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.notification_templates"
      :total-count="assetsStore.notification_templates.total_count"
      total-count-title="notification_template.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewNotificationTemplate :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="assetsStore.notification_templates.items"
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
import { deleteNotificationTemplate } from '@/api/assets'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewNotificationTemplate from '@/components/config/notifications/NewNotificationTemplate.vue'

const { t } = useI18n()
const assetsStore = useAssetsStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await assetsStore.loadNotificationTemplates(filter.value)
  } catch (error) {
    console.error('Error loading notification templates:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (template) => {
  try {
    await deleteNotificationTemplate(template)
    console.log('Notification template deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting notification template:', error)
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
