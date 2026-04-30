<template>
  <v-dialog v-model="dialog" max-width="800" persistent>
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
          {{ isEdit ? t('osint_source.edit') : t('osint_source.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="localItem.name"
            :label="t('osint_source.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-textarea
            v-model="localItem.description"
            :label="t('osint_source.description')"
            variant="outlined"
            density="comfortable"
            rows="3"
            class="mb-3"
            :disabled="saving"
          />

          <v-text-field
            v-model="localItem.feed_url"
            :label="t('osint_source.feed_url')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-select
            v-model="localItem.collector"
            :label="t('osint_source.collector')"
            :items="collectorTypes"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-text-field
            v-model.number="localItem.refresh_interval"
            :label="t('osint_source.refresh_interval')"
            variant="outlined"
            density="comfortable"
            type="number"
            class="mb-3"
            :disabled="saving"
          />

          <v-switch
            v-model="localItem.enabled"
            :label="t('osint_source.enabled')"
            color="primary"
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
          {{ t('osint_source.error') }}
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
import { createNewOSINTSource, updateOSINTSource } from '@/api/config'

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

const collectorTypes = [
  { title: 'RSS Collector', value: 'rss_collector' },
  { title: 'Web Collector', value: 'web_collector' },
  { title: 'RT Collector', value: 'rt_collector' },
  { title: 'Email Collector', value: 'email_collector' },
  { title: 'Twitter Collector', value: 'twitter_collector' },
  { title: 'Simple Collector', value: 'simple_collector' }
]

const defaultItem = {
  id: null,
  name: '',
  description: '',
  feed_url: '',
  collector: 'rss_collector',
  refresh_interval: 60,
  enabled: true
}

const localItem = ref({ ...defaultItem })

const canCreate = computed(() => checkPermission('CONFIG_OSINT_SOURCE_CREATE'))

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
      await updateOSINTSource(localItem.value)
    } else {
      await createNewOSINTSource(localItem.value)
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
