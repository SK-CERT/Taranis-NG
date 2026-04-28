<template>
  <v-dialog v-model="dialog" max-width="600" persistent>
    <template #activator="{ props: activatorProps }">
      <v-btn
        v-if="canCreate"
        v-bind="activatorProps"
        color="primary"
        prepend-icon="mdi-plus"
      >
        {{ t('common.add_btn') }}
      </v-btn>
    </template>

    <v-card>
      <v-card-title>
        <span class="text-h5">
          {{ isEdit ? t('data_provider.edit') : t('data_provider.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="localItem.name"
            :label="t('data_provider.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-select
            v-model="localItem.api_type"
            :label="t('data_provider.api_type')"
            :items="['CVE', 'CWE', 'CPE', 'EUVD', 'EPSS']"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.api_url"
            :label="t('data_provider.api_url')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-row class="mb-2">
            <v-col cols="6">
              <v-text-field
                v-model="localItem.api_key"
                :label="t('settings.api_key')"
                variant="outlined"
                density="comfortable"
                :type="showApiKey ? 'text' : 'password'"
                :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                :disabled="saving"
                @click:append-inner="showApiKey = !showApiKey"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="localItem.user_agent"
                :label="t('data_provider.user_agent')"
                variant="outlined"
                density="comfortable"
                :disabled="saving"
              />
            </v-col>
          </v-row>

          <v-text-field
            v-model="localItem.web_url"
            :label="t('data_provider.web_url')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :disabled="saving"
          />
        </v-form>

        <v-alert
          v-if="showValidationError"
          type="error"
          variant="tonal"
          class="mt-4"
          closable
          @click:close="showValidationError = false"
        >
          {{ t('error.validation') }}
        </v-alert>

        <v-alert
          v-if="showError"
          type="error"
          variant="tonal"
          class="mt-4"
          closable
          @click:close="showError = false"
        >
          {{ t('data_provider.error') }}
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="grey"
          variant="text"
          :disabled="saving"
          @click="handleCancel"
        >
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="text"
          :loading="saving"
          @click="handleSubmit"
        >
          <v-icon left>mdi-content-save</v-icon>
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import { useAuth } from '@/composables/useAuth'
import { createNewDataProvider, updateDataProvider } from '@/api/config'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  item: {
    type: Object,
    default: () => ({})
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const { checkPermission } = useAuth()

const formRef = ref(null)
const showValidationError = ref(false)
const showError = ref(false)
const saving = ref(false)
const dialog = ref(false)
const showApiKey = ref(false)

const defaultItem = {
  id: null,
  name: 'ENISA EUVD',
  api_type: 'EUVD',
  api_url: 'https://euvdservices.enisa.europa.eu/api/',
  api_key: '',
  user_agent: '',
  web_url: ''
}

const localItem = ref({ ...defaultItem })

const canCreate = computed(() => checkPermission('CONFIG_DATA_PROVIDER_CREATE'))

async function handleSubmit() {
  showValidationError.value = false
  showError.value = false

  const { valid } = await formRef.value.validate()
  if (!valid) {
    showValidationError.value = true
    return
  }

  saving.value = true
  try {
    if (props.isEdit) {
      await updateDataProvider(localItem.value)
    } else {
      await createNewDataProvider(localItem.value)
    }
    emit('saved')
    handleCancel()
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

function handleCancel() {
  showValidationError.value = false
  showError.value = false
  formRef.value?.reset()
  localItem.value = { ...defaultItem }
  dialog.value = false
  showApiKey.value = false
}

watch(
  () => props.item,
  (newItem) => {
    if (newItem && Object.keys(newItem).length > 0) {
      localItem.value = { ...newItem }
    } else {
      localItem.value = { ...defaultItem }
    }
  },
  { immediate: true, deep: true }
)

watch(
  () => dialog.value,
  (newVal) => {
    if (!newVal) {
      showValidationError.value = false
      showError.value = false
      saving.value = false
      showApiKey.value = false
    }
  }
)
</script>
