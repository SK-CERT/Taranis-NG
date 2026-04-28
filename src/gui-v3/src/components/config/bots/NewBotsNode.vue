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
          {{ isEdit ? t('bots_node.edit') : t('bots_node.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="localItem.name"
            :label="t('bots_node.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-textarea
            v-model="localItem.description"
            :label="t('bots_node.description')"
            variant="outlined"
            density="comfortable"
            rows="3"
            class="mb-3"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.api_url"
            :label="t('bots_node.url')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.api_key"
            :label="t('bots_node.key')"
            :type="showApiKey ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
            :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
            @click:append-inner="showApiKey = !showApiKey"
          />

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
            {{ t('bots_node.error') }}
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
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import { useAuth } from '@/composables/useAuth'
import { createNewBotsNode, updateBotsNode } from '@/api/config'

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
const showApiKey = ref(false)

const defaultItem = {
  id: null,
  name: '',
  description: '',
  api_url: '',
  api_key: ''
}

const localItem = ref({ ...defaultItem })

const isEdit = computed(() => !!localItem.value.id)
const canCreate = computed(() => checkPermission('CONFIG_BOTS_NODE_CREATE'))

watch(
  () => props.editItem,
  (newVal) => {
    if (newVal) {
      localItem.value = { ...newVal }
      dialog.value = true
    }
  },
  { immediate: true, deep: true }
)

watch(dialog, (newVal) => {
  if (!newVal) {
    resetForm()
  }
  emit('update:modelValue', newVal)
})

const resetForm = () => {
  localItem.value = { ...defaultItem }
  showValidationError.value = false
  showError.value = false
  showApiKey.value = false
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
    if (isEdit.value) {
      await updateBotsNode(localItem.value)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.updated_successfully' }
        })
      )
    } else {
      await createNewBotsNode(localItem.value)
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
