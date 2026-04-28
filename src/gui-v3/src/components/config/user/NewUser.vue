<template>
  <v-dialog
    v-model="dialog"
    max-width="1000"
    persistent
    scrollable
  >
    <template #activator="{ props: activatorProps }">
      <AddNewButton :show="canCreate" v-bind="activatorProps" />
    </template>

    <v-card>
      <v-card-title>
        <span class="text-h5">
          {{ isEdit ? t('user.edit') : t('user.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model="localItem.username"
                :label="t('user.username')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="localItem.name"
                :label="t('user.name')"
                variant="outlined"
                density="comfortable"
                :disabled="saving"
              />
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model="password"
                :label="t('user.password')"
                :type="showPassword ? 'text' : 'password'"
                variant="outlined"
                density="comfortable"
                :rules="passwordRules"
                :disabled="saving"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="passwordConfirm"
                :label="t('user.password_check')"
                :type="showPassword ? 'text' : 'password'"
                variant="outlined"
                density="comfortable"
                :rules="passwordConfirmRules"
                :disabled="saving"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
              />
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <!-- Organizations Selection -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              {{ t('user.organizations') }}
            </v-card-title>
            <v-data-table
              v-model="selectedOrganizations"
              :headers="orgHeaders"
              :items="organizations"
              :loading="loadingOrganizations"
              item-value="id"
              show-select
              density="comfortable"
              :disabled="saving"
            >
              <template #item.name="{ item }">
                <strong>{{ item.name }}</strong>
              </template>
            </v-data-table>
          </v-card>

          <!-- Roles Selection -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              {{ t('user.roles') }}
            </v-card-title>
            <v-data-table
              v-model="selectedRoles"
              :headers="roleHeaders"
              :items="roles"
              :loading="loadingRoles"
              item-value="id"
              show-select
              density="comfortable"
              :disabled="saving"
            >
              <template #item.name="{ item }">
                <strong>{{ item.name }}</strong>
              </template>
            </v-data-table>
          </v-card>

          <!-- Permissions Selection -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 bg-grey-lighten-4">
              {{ t('user.permissions') }}
            </v-card-title>
            <v-data-table
              v-model="selectedPermissions"
              :headers="permissionHeaders"
              :items="permissions"
              :loading="loadingPermissions"
              item-value="id"
              show-select
              density="comfortable"
              :disabled="saving"
            >
              <template #item.name="{ item }">
                <strong>{{ item.name }}</strong>
              </template>
            </v-data-table>
          </v-card>

          <v-alert
            v-if="showValidationError"
            type="error"
            density="compact"
            class="mb-3"
          >
            {{ t('error.validation') }}
          </v-alert>

          <v-alert
            v-if="showError"
            type="error"
            density="compact"
            class="mb-3"
          >
            {{ t('user.error') }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="grey"
          variant="text"
          :disabled="saving"
          @click="cancel"
        >
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="text"
          :loading="saving"
          :disabled="saving"
          @click="handleSubmit"
        >
          <v-icon start>mdi-content-save</v-icon>
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import {
  createNewUser,
  updateUser,
  getAllOrganizations,
  getAllRoles,
  getAllPermissions
} from '@/api/config'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const { checkPermission } = useAuth()

const dialog = ref(false)
const formRef = ref(null)
const saving = ref(false)
const showValidationError = ref(false)
const showError = ref(false)
const showPassword = ref(false)

const password = ref('')
const passwordConfirm = ref('')

const organizations = ref([])
const roles = ref([])
const permissions = ref([])

const loadingOrganizations = ref(false)
const loadingRoles = ref(false)
const loadingPermissions = ref(false)

const selectedOrganizations = ref([])
const selectedRoles = ref([])
const selectedPermissions = ref([])

const defaultItem = {
  id: null,
  username: '',
  name: '',
  organizations: [],
  roles: [],
  permissions: []
}

const localItem = ref({ ...defaultItem })

const isEdit = computed(() => !!localItem.value.id)
const canCreate = computed(() => checkPermission('CONFIG_USER_CREATE'))

const passwordRules = computed(() => {
  if (isEdit.value) {
    // For edit, password is optional unless filled
    return password.value ? [(v) => !!v || t('error.required')] : []
  }
  // For new user, password is required
  return [(v) => !!v || t('error.required')]
})

const passwordConfirmRules = computed(() => {
  if (isEdit.value && !password.value) {
    return []
  }
  return [
    (v) => !!v || t('error.required'),
    (v) => v === password.value || t('user.password_mismatch')
  ]
})

const orgHeaders = [
  { title: t('user.name'), key: 'name', sortable: true },
  { title: t('user.description'), key: 'description', sortable: false }
]

const roleHeaders = [
  { title: t('user.name'), key: 'name', sortable: true },
  { title: t('user.description'), key: 'description', sortable: false }
]

const permissionHeaders = [
  { title: t('user.name'), key: 'name', sortable: true },
  { title: t('user.description'), key: 'description', sortable: false }
]

// Watch for edit item changes
watch(
  () => props.editItem,
  (newVal) => {
    if (newVal) {
      localItem.value = { ...newVal }

      // Set selected items
      selectedOrganizations.value = newVal.organizations?.map((org) => org.id) || []
      selectedRoles.value = newVal.roles?.map((role) => role.id) || []
      selectedPermissions.value = newVal.permissions?.map((perm) => perm.id) || []

      // Reset passwords
      password.value = ''
      passwordConfirm.value = ''

      dialog.value = true
    }
  },
  { immediate: true, deep: true }
)

// Watch dialog state
watch(dialog, (newVal) => {
  if (!newVal) {
    resetForm()
  }
  emit('update:modelValue', newVal)
})

// Load data on mount
onMounted(async () => {
  await loadAllData()
})

const loadAllData = async () => {
  loadingOrganizations.value = true
  loadingRoles.value = true
  loadingPermissions.value = true

  try {
    const [orgsResponse, rolesResponse, permsResponse] = await Promise.all([
      getAllOrganizations({ search: '' }),
      getAllRoles({ search: '' }),
      getAllPermissions({ search: '' })
    ])

    organizations.value = orgsResponse.items || []
    roles.value = rolesResponse.items || []
    permissions.value = permsResponse.items || []
  } catch (error) {
    console.error('Error loading user data:', error)
  } finally {
    loadingOrganizations.value = false
    loadingRoles.value = false
    loadingPermissions.value = false
  }
}

const resetForm = () => {
  localItem.value = { ...defaultItem }
  password.value = ''
  passwordConfirm.value = ''
  selectedOrganizations.value = []
  selectedRoles.value = []
  selectedPermissions.value = []
  showValidationError.value = false
  showError.value = false
  showPassword.value = false
  if (formRef.value) {
    formRef.value.resetValidation()
  }
}

const cancel = () => {
  dialog.value = false
}

const handleSubmit = async () => {
  showValidationError.value = false
  showError.value = false

  const { valid } = await formRef.value.validate()

  if (!valid) {
    showValidationError.value = true
    return
  }

  saving.value = true

  try {
    const payload = {
      ...localItem.value,
      organizations: selectedOrganizations.value.map((id) => ({ id })),
      roles: selectedRoles.value.map((id) => ({ id })),
      permissions: selectedPermissions.value.map((id) => ({ id }))
    }

    // Add password if provided
    if (password.value) {
      payload.password = password.value
    }

    if (isEdit.value) {
      await updateUser(payload)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.updated_successfully' }
        })
      )
    } else {
      await createNewUser(payload)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.created_successfully' }
        })
      )
    }

    dialog.value = false
    emit('saved')
  } catch (error) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'common.error_saving' }
      })
    )
    showError.value = true
  } finally {
    saving.value = false
  }
}
</script>
