<template>
  <v-container fluid>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-tooltip location="right">
          <template #activator="{ props }">
            <v-icon v-bind="props" color="blue" class="me-2">
              mdi-help-circle
            </v-icon>
          </template>
          <span>{{ t('data_provider.data_providers.tab_description') }}</span>
        </v-tooltip>
        <span>{{ t('nav_menu.data_providers') }}</span>
      </v-card-title>

      <!-- Toolbar -->
      <v-card-text>
        <v-row>
          <v-col cols="8">
            <v-text-field
              v-model="search"
              :label="t('toolbar_filter.search')"
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
              single-line
            />
          </v-col>
          <v-col cols="4" class="text-right">
            <NewDataProvider @saved="handleSaved" />
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="configStore.dataProviders.items"
        :search="search"
        item-key="id"
        class="elevation-1"
      >
        <template #item.name="{ item }">
          <strong>{{ item.name }}</strong>
        </template>

        <template #item.api_key="{ item }">
          {{ item.api_key ? '••••••••' : '' }}
        </template>

        <template #item.updated_at="{ item }">
          {{ item.updated_at ? new Date(item.updated_at).toLocaleString() : '' }}
        </template>

        <template #item.actions="{ item }">
          <ActionButton
            action="edit"
            :title="t('common.edit')"
            class="mr-1"
            @click="handleEdit(item)"
          />
          <ActionButton
            action="delete"
            :title="t('common.delete')"
            @click="handleDelete(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Edit Dialog -->
    <v-dialog v-model="showEditDialog" max-width="800">
      <NewDataProvider :edit-item="editItem" @saved="handleSaved" />
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { deleteDataProvider } from '@/api/config'
import NewDataProvider from '@/components/config/data-providers/NewDataProvider.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const search = ref('')
const showEditDialog = ref(false)
const editItem = ref(null)

const headers = [
  { title: t('data_provider.name'), key: 'name' },
  { title: t('data_provider.api_type'), key: 'api_type' },
  { title: t('data_provider.api_url'), key: 'api_url' },
  { title: t('settings.api_key'), key: 'api_key', sortable: false },
  { title: t('data_provider.user_agent'), key: 'user_agent' },
  { title: t('data_provider.web_url'), key: 'web_url' },
  { title: t('settings.updated_by'), key: 'updated_by' },
  { title: t('settings.updated_at'), key: 'updated_at', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false }
]

const loadData = async () => {
  try {
    await configStore.loadDataProviders({ search: search.value })
  } catch (error) {
    console.error('Error loading data providers:', error)
  }
}

const handleEdit = (item) => {
  editItem.value = item
  showEditDialog.value = true
}

const handleDelete = async (item) => {
  if (confirm(t('common.messagebox.delete_confirm', { name: item.name }))) {
    try {
      await deleteDataProvider(item)
      await loadData()
    } catch (error) {
      console.error('Error deleting data provider:', error)
    }
  }
}

const handleSaved = () => {
  showEditDialog.value = false
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
