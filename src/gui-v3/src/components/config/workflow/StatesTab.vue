<template>
  <v-container fluid>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <v-icon color="blue" v-bind="props" class="mr-2">mdi-information-outline</v-icon>
          </template>
          <span>{{ t('workflow.states.tab_description') }}</span>
        </v-tooltip>
        <span>{{ t('workflow.states_tab') }}</span>
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
            <AddNewButton :show="canCreate" @click="addItem" />
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="filteredRecords"
        :search="search"
        item-key="id"
        class="elevation-1"
      >
        <template #item.display_name="{ item }">
          {{ t(`workflow.states.${item.display_name}`, item.display_name) }}
        </template>

        <template #item.color="{ item }">
          <v-chip :color="item.color" label :text-color="getContrastColor(item.color)">
            {{ item.color }}
          </v-chip>
        </template>

        <template #item.icon="{ item }">
          <v-icon :color="item.color">{{ item.icon }}</v-icon>
        </template>

        <template #item.actions="{ item }">
          <template v-if="item.editable">
            <ActionButton
              action="edit"
              :title="t('common.edit')"
              class="mr-1"
              @click="editItem(item)"
            />
            <ActionButton
              action="delete"
              :title="t('common.delete')"
              @click="deleteItem(item)"
            />
          </template>
          <template v-else>
            <ActionButton
              action="lock"
              :title="t('workflow.states.cannot_edit_system_state')"
            />
          </template>
        </template>
      </v-data-table>
    </v-card>

    <!-- Delete Dialog -->
    <v-dialog v-model="dialogDelete" max-width="500">
      <v-card>
        <v-card-title>{{ t('common.messagebox.delete') }}</v-card-title>
        <v-card-text>
          {{ t('common.messagebox.delete_confirm', { name: editedItem.display_name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="closeDelete">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="text" @click="deleteRecord">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit Dialog - Simplified for now -->
    <v-dialog v-model="dialogEdit" max-width="700">
      <v-card>
        <v-card-title>
          {{ editedIndex === -1 ? t('workflow.states.add_new') : t('workflow.states.edit') }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="editedItem.display_name"
              :label="t('workflow.states.display_name')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              :rules="[(v) => !!v || t('error.required')]"
            />

            <v-textarea
              v-model="editedItem.description"
              :label="t('workflow.states.description')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              rows="3"
              class="mb-3"
            />

            <v-text-field
              v-model="editedItem.color"
              :label="t('workflow.states.color')"
              :disabled="!isEditable"
              variant="outlined"
              type="color"
              density="comfortable"
              class="mb-3"
            />

            <v-text-field
              v-model="editedItem.icon"
              :label="t('workflow.states.icon')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              placeholder="mdi-circle"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="closeEdit">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            v-if="isEditable"
            color="primary"
            variant="text"
            @click="saveRecord"
          >
            <v-icon left>mdi-content-save</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import { useConfigStore } from '@/stores/config'
import { useAuth } from '@/composables/useAuth'
import {
  createNewStateDefinition,
  updateStateDefinition,
  deleteStateDefinition
} from '@/api/config'

const { t } = useI18n()
const configStore = useConfigStore()
const { checkPermission } = useAuth()

const search = ref('')
const dialogEdit = ref(false)
const dialogDelete = ref(false)
const editedIndex = ref(-1)
const formRef = ref(null)

const defaultItem = {
  id: -1,
  display_name: '',
  description: '',
  color: '#2196F3',
  icon: 'mdi-circle',
  editable: true
}

const editedItem = ref({ ...defaultItem })

const headers = [
  { title: t('workflow.states.display_name'), key: 'display_name' },
  { title: t('workflow.states.description'), key: 'description' },
  { title: t('workflow.states.color'), key: 'color' },
  { title: t('workflow.states.icon'), key: 'icon' },
  { title: t('settings.actions'), key: 'actions', sortable: false }
]

const canCreate = computed(() => checkPermission('CONFIG_WORKFLOW_CREATE'))

const isEditable = computed(() => editedIndex.value === -1 || editedItem.value.editable)

const filteredRecords = computed(() => configStore.stateDefinitions.items || [])

function getContrastColor(hexColor) {
  if (!hexColor || hexColor.length < 7) return 'white'
  const r = parseInt(hexColor.slice(1, 3), 16)
  const g = parseInt(hexColor.slice(3, 5), 16)
  const b = parseInt(hexColor.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? 'black' : 'white'
}

function addItem() {
  editedIndex.value = -1
  editedItem.value = { ...defaultItem }
  dialogEdit.value = true
}

function editItem(item) {
  const records = configStore.stateDefinitions.items
  editedIndex.value = records.indexOf(item)
  editedItem.value = { ...item }
  dialogEdit.value = true
}

function deleteItem(item) {
  if (!item.editable) return
  const records = configStore.stateDefinitions.items
  editedIndex.value = records.indexOf(item)
  editedItem.value = { ...item }
  dialogDelete.value = true
}

function closeEdit() {
  dialogEdit.value = false
  setTimeout(() => {
    editedItem.value = { ...defaultItem }
    editedIndex.value = -1
  }, 300)
}

function closeDelete() {
  dialogDelete.value = false
  setTimeout(() => {
    editedItem.value = { ...defaultItem }
    editedIndex.value = -1
  }, 300)
}

async function saveRecord() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  try {
    if (editedIndex.value > -1) {
      await updateStateDefinition(editedItem.value)
    } else {
      await createNewStateDefinition(editedItem.value)
    }
    await configStore.loadStateDefinitions({ search: '' })
    closeEdit()
  } catch (error) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'common.error_saving' }
      })
    )
  }
}

async function deleteRecord() {
  if (!editedItem.value.editable) {
    closeDelete()
    return
  }

  try {
    await deleteStateDefinition(editedItem.value)
    await configStore.loadStateDefinitions({ search: '' })
    closeDelete()
  } catch (error) {
    console.error('Error deleting state:', error)
  }
}

onMounted(() => {
  if (checkPermission('CONFIG_WORKFLOW_ACCESS')) {
    configStore.loadStateDefinitions({ search: '' })
  }
})
</script>
