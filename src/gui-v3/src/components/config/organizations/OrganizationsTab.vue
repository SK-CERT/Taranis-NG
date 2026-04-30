<template>
  <v-container fluid>
    <v-card>
      <v-card-title class="d-flex align-center">
        <span>{{ t('nav_menu.organizations') }}</span>
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
            <NewOrganization @saved="handleSaved" />
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="configStore.organizations.items"
        :search="search"
        item-key="id"
        class="elevation-1"
      >
        <template #item.name="{ item }">
          <strong>{{ item.name }}</strong>
        </template>

        <template #item.description="{ item }">
          {{ item.description }}
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
      <NewOrganization :edit-item="editItem" @saved="handleSaved" />
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { deleteOrganization } from '@/api/config'
import NewOrganization from '@/components/config/organizations/NewOrganization.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const search = ref('')
const showEditDialog = ref(false)
const editItem = ref(null)

const headers = [
  { title: t('organization.name'), key: 'name' },
  { title: t('organization.description'), key: 'description' },
  { title: t('common.actions'), key: 'actions', sortable: false }
]

const loadData = async () => {
  try {
    await configStore.loadOrganizations({ search: search.value })
  } catch (error) {
    console.error('Error loading organizations:', error)
  }
}

const handleEdit = (item) => {
  editItem.value = item
  showEditDialog.value = true
}

const handleDelete = async (item) => {
  if (confirm(t('common.messagebox.delete_confirm', { name: item.name }))) {
    try {
      await deleteOrganization(item)
      await loadData()
    } catch (error) {
      console.error('Error deleting organization:', error)
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
