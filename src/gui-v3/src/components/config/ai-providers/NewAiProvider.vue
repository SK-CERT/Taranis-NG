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
          {{ isEdit ? t('ai_provider.edit') : t('ai_provider.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="localItem.name"
            :label="t('ai_provider.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-select
            v-model="localItem.api_type"
            :label="t('ai_provider.api_type')"
            :items="['openai']"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.api_url"
            :label="t('ai_provider.api_url')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.api_key"
            :label="t('settings.api_key')"
            variant="outlined"
            density="comfortable"
            :type="showApiKey ? 'text' : 'password'"
            class="mb-3"
            :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
            @click:append-inner="showApiKey = !showApiKey"
          />

          <v-text-field
            v-model="localItem.model"
            :label="t('ai_provider.model')"
            variant="outlined"
            density="comfortable"
            :rules="[(v) => !!v || t('error.required')]"
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
          {{ t('ai_provider.error') }}
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
import { useAuth } from '@/composables/useAuth'
import { createNewAiProvider, updateAiProvider } from '@/api/config'

const props = defineProps({
  editItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['saved'])

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
  name: '',
  api_type: 'openai',
  api_url: '',
  api_key: '',
  model: ''
}

const localItem = ref({ ...defaultItem })

const isEdit = computed(() => !!localItem.value.id)
const canCreate = computed(() => checkPermission('CONFIG_AI_CREATE'))

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
    if (isEdit.value) {
      await updateAiProvider(localItem.value)
    } else {
      await createNewAiProvider(localItem.value)
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
  () => props.editItem,
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
