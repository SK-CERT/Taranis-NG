<template>
  <v-dialog
    v-model="dialog"
    max-width="600px"
    persistent
    scrollable
  >
    <!-- Activator Button - handled by parent -->
    <v-card>
      <v-card-title>
        {{ $t('asset.add_new') }}
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef">
          <v-text-field
            v-model="form.title"
            :label="$t('asset.title')"
            :rules="[requiredRule]"
            required
          />
          <v-text-field
            v-model="form.description"
            :label="$t('asset.description')"
          />
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="closeDialog">{{ $t('common.cancel') }}</v-btn>
        <v-btn color="primary" @click="save">{{ $t('common.save') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'

const { t } = useI18n()
const { checkPermission } = useAuth()

const dialog = ref(false)
const form = ref({
  title: '',
  description: ''
})
const formRef = ref(null)

const requiredRule = (value) => !!value || t('common.required')
const canCreate = computed(() => checkPermission('MY_ASSETS_CREATE'))

const closeDialog = () => {
  dialog.value = false
  form.value = {
    title: '',
    description: ''
  }
  formRef.value?.reset()
}

const save = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  try {
    // TODO: Implement actual asset creation API call
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'asset.created_successfully' }
      })
    )
    window.dispatchEvent(new CustomEvent('asset-created'))
    closeDialog()
  } catch (error) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'asset.error' }
      })
    )
  }
}

defineExpose({
  openDialog: () => {
    dialog.value = true
  },
  closeDialog
})
</script>
