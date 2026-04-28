<template>
  <v-container fluid>
    <v-card>
      <v-card-title class="d-flex align-center">
        <span>{{ t('nav_menu.users') }}</span>
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
            <NewUser ref="newUserRef" @saved="handleSaved" />
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="configStore.users.items"
        :search="search"
        item-key="id"
        class="elevation-1"
      >
        <template #item.username="{ item }">
          <strong>{{ item.username }}</strong>
        </template>

        <template #item.name="{ item }">
          {{ item.name }}
        </template>

        <template #item.organizations="{ item }">
          <v-chip
            v-for="org in item.organizations"
            :key="org.id"
            size="small"
            class="mr-1"
          >
            {{ org.name }}
          </v-chip>
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
      <NewUser ref="newUserRef" :edit-item="editItem" @saved="handleSaved" />
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { deleteUser } from '@/api/config'
import NewUser from '@/components/config/user/NewUser.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const search = ref('')
const showEditDialog = ref(false)
const editItem = ref(null)
const newUserRef = ref(null)

const headers = [
  { title: t('user.username'), key: 'username' },
  { title: t('user.name'), key: 'name' },
  { title: t('user.organizations'), key: 'organizations' },
  { title: t('common.actions'), key: 'actions', sortable: false }
]

const loadData = async () => {
  try {
    await configStore.loadUsers({ search: search.value })
  } catch (error) {
    console.error('Error loading users:', error)
  }
}

const handleEdit = (item) => {
  editItem.value = item
  showEditDialog.value = true
}

const handleDelete = async (item) => {
  if (confirm(t('common.messagebox.delete_confirm', { name: item.username }))) {
    try {
      await deleteUser(item)
      await loadData()
    } catch (error) {
      console.error('Error deleting user:', error)
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
