<template>
  <v-dialog v-model="dialog" max-width="600" persistent>
    <template #activator="{ props: activatorProps }">
      <AddNewButton :show="canCreate" v-bind="activatorProps" />
    </template>

    <v-card>
      <v-card-title>
        <span class="text-h5">
          {{ isEdit ? t('attribute.edit') : t('attribute.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="localItem.name"
            :label="t('attribute.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-textarea
            v-model="localItem.description"
            :label="t('attribute.description')"
            variant="outlined"
            density="comfortable"
            rows="3"
            class="mb-3"
            :disabled="saving"
          />

          <v-select
            v-model="localItem.type"
            :label="t('attribute.type')"
            :items="attributeTypes"
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
          {{ t('attribute.error') }}
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
import { createNewAttribute, updateAttribute } from '@/api/config'

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

const attributeTypes = [
  { title: 'STRING', value: 'STRING' },
  { title: 'NUMBER', value: 'NUMBER' },
  { title: 'BOOLEAN', value: 'BOOLEAN' },
  { title: 'DATE', value: 'DATE' },
  { title: 'DATETIME', value: 'DATETIME' },
  { title: 'TEXT', value: 'TEXT' },
  { title: 'ENUM', value: 'ENUM' }
]

const defaultItem = {
  id: null,
  name: '',
  description: '',
  type: 'STRING'
}

const localItem = ref({ ...defaultItem })

const canCreate = computed(() => checkPermission('CONFIG_ATTRIBUTE_CREATE'))

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
      await updateAttribute(localItem.value)
    } else {
      await createNewAttribute(localItem.value)
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
    }
  }
)
</script>
