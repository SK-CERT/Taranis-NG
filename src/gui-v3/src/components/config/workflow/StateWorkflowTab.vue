<template>
  <v-container fluid>
    <v-card class="mt-4">
      <v-card-title class="d-flex align-center">
        <v-tooltip location="top">
          <template #activator="{ props }">
            <v-icon color="blue" v-bind="props" class="mr-2">mdi-information-outline</v-icon>
          </template>
          <span>{{ t('workflow.state_workflow.tab_description') }}</span>
        </v-tooltip>
        <span>{{ t('workflow.state_workflow_tab') }}</span>
      </v-card-title>

      <!-- Toolbar -->
      <v-card-text>
        <v-row>
          <v-col cols="6">
            <v-select
              v-model="filterEntityType"
              :items="entityTypeFilter"
              :label="t('workflow.state_workflow.filter_by_entity_type')"
              variant="outlined"
              density="compact"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="6" class="text-right">
            <AddNewButton :show="canCreate" @click="addItem" />
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="filteredRecords"
        item-key="id"
        class="elevation-1"
      >
        <template #item.entity_type="{ item }">
          <v-chip label :color="getEntityTypeColor(item.entity_type)">
            <v-icon start>{{ getEntityTypeIcon(item.entity_type) }}</v-icon>
            {{ t(`workflow.entity_types.${item.entity_type}`) }}
          </v-chip>
        </template>

        <template #item.state_name="{ item }">
          <v-icon v-if="item.state" start :color="item.state.color">
            {{ item.state.icon }}
          </v-icon>
          {{
            item.state
              ? t(`workflow.states.${item.state.display_name}`, item.state.display_name)
              : '-'
          }}
        </template>

        <template #item.state_type="{ item }">
          <v-chip label color="grey">
            <v-icon start>{{ getStateTypeIcon(item.state_type) }}</v-icon>
            {{ t(`workflow.state_types.${item.state_type}`) }}
          </v-chip>
        </template>

        <template #item.is_active="{ item }">
          <v-icon :color="item.is_active ? 'green' : 'error'">
            {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
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
              :title="t('workflow.state_workflow.cannot_edit_system_association')"
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
          {{ t('common.messagebox.delete_confirm_item') }}
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

    <!-- Edit Dialog - Simplified -->
    <v-dialog v-model="dialogEdit" max-width="700">
      <v-card>
        <v-card-title>
          {{
            editedIndex === -1
              ? t('workflow.state_workflow.add_new')
              : t('workflow.state_workflow.edit')
          }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-select
              v-model="editedItem.entity_type"
              :items="entityTypeFilter"
              :label="t('workflow.state_workflow.entity_type')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              :rules="[(v) => !!v || t('error.required')]"
            />

            <v-select
              v-model="editedItem.state_id"
              :items="availableStates"
              item-title="display_name"
              item-value="id"
              :label="t('workflow.state_workflow.state')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              :rules="[(v) => !!v || t('error.required')]"
            />

            <v-select
              v-model="editedItem.state_type"
              :items="stateTypeOptions"
              :label="t('workflow.state_workflow.state_type')"
              :disabled="!isEditable"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <v-text-field
              v-model.number="editedItem.sort_order"
              :label="t('workflow.state_workflow.sort_order')"
              :disabled="!isEditable"
              variant="outlined"
              type="number"
              density="comfortable"
              class="mb-3"
            />

            <v-switch
              v-model="editedItem.is_active"
              :label="t('workflow.state_workflow.is_active')"
              :disabled="!isEditable"
              color="primary"
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
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import ActionButton from '@/components/common/buttons/ActionButton.vue'
import { useConfigStore } from '@/stores/config'
import { useAuth } from '@/composables/useAuth'
import {
  createNewStateEntityType,
  updateStateEntityType,
  deleteStateEntityType
} from '@/api/config'

const { t } = useI18n()
const configStore = useConfigStore()
const { checkPermission } = useAuth()

const filterEntityType = ref(null)
const dialogEdit = ref(false)
const dialogDelete = ref(false)
const editedIndex = ref(-1)
const formRef = ref(null)

const defaultItem = {
  id: -1,
  entity_type: '',
  state_id: null,
  state_type: 'normal',
  is_active: true,
  editable: true,
  sort_order: 0
}

const editedItem = ref({ ...defaultItem })

const headers = [
  { title: t('workflow.state_workflow.entity_type'), key: 'entity_type' },
  { title: t('workflow.state_workflow.state'), key: 'state_name' },
  { title: t('workflow.state_workflow.state_type'), key: 'state_type' },
  { title: t('workflow.state_workflow.is_active'), key: 'is_active' },
  { title: t('workflow.state_workflow.sort_order'), key: 'sort_order' },
  { title: t('settings.actions'), key: 'actions', sortable: false }
]

const entityTypeFilter = [
  { title: t('workflow.entity_types.product'), value: 'product' },
  { title: t('workflow.entity_types.report_item'), value: 'report_item' }
]

const stateTypeOptions = [
  { title: t('workflow.state_types.initial'), value: 'initial' },
  { title: t('workflow.state_types.normal'), value: 'normal' },
  { title: t('workflow.state_types.final'), value: 'final' }
]

const canCreate = computed(() => checkPermission('CONFIG_WORKFLOW_CREATE'))

const isEditable = computed(() => editedIndex.value === -1 || editedItem.value.editable)

const availableStates = computed(() => configStore.stateDefinitions.items || [])

const filteredRecords = computed(() => configStore.stateEntityTypes.items || [])

function getEntityTypeColor(entityType) {
  const colors = {
    report_item: '#2196F3',
    product: '#4CAF50'
  }
  return colors[entityType] || 'grey'
}

function getEntityTypeIcon(entityType) {
  const icons = {
    report_item: 'mdi-file-document',
    product: 'mdi-package-variant'
  }
  return icons[entityType] || 'mdi-help'
}

function getStateTypeIcon(stateType) {
  const icons = {
    normal: 'mdi-circle',
    initial: 'mdi-star',
    final: 'mdi-flag-checkered'
  }
  return icons[stateType] || 'mdi-help'
}

async function fetchRecords() {
  if (!checkPermission('CONFIG_WORKFLOW_ACCESS')) return

  // Load state definitions first
  await configStore.loadStateDefinitions({ search: '' })

  // Then load state-entity type associations
  const filter = {}
  if (filterEntityType.value) {
    filter.entity_type = filterEntityType.value
  }
  await configStore.loadStateEntityTypes(filter)
}

function addItem() {
  editedIndex.value = -1
  editedItem.value = { ...defaultItem }
  dialogEdit.value = true
}

function editItem(item) {
  const records = configStore.stateEntityTypes.items
  editedIndex.value = records.indexOf(item)
  editedItem.value = { ...item }
  dialogEdit.value = true
}

function deleteItem(item) {
  if (!item.editable) return
  const records = configStore.stateEntityTypes.items
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
      await updateStateEntityType(editedItem.value)
    } else {
      await createNewStateEntityType(editedItem.value)
    }
    await fetchRecords()
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
    await deleteStateEntityType(editedItem.value)
    await fetchRecords()
    closeDelete()
  } catch (error) {
    console.error('Error deleting state entity type:', error)
  }
}

watch(filterEntityType, () => {
  fetchRecords()
})

onMounted(() => {
  fetchRecords()
})
</script>
