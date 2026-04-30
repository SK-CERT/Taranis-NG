<template>
  <v-dialog
    v-model="visible"
    max-width="900px"
    persistent
    @keydown.esc="handleCancel"
  >
    <!-- Confirmation Dialog -->
    <v-dialog v-model="showCloseConfirmation" max-width="500px" persistent>
      <v-card>
        <v-card-title>{{ $t('confirm_close.title') }}</v-card-title>
        <v-card-text>{{ $t('confirm_close.message') }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showCloseConfirmation = false">{{ $t('confirm_close.continue') }}</v-btn>
          <v-btn color="primary" @click="confirmClose">{{ $t('confirm_close.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Main Dialog -->
    <v-card>
      <v-toolbar color="primary" dark>
        <v-btn icon @click="handleCancel">
          <v-icon>mdi-close</v-icon>
        </v-btn>
        <v-toolbar-title>
          {{ $t('asset.detail') }}
        </v-toolbar-title>
        <v-spacer />
      </v-toolbar>

      <!-- Tabs Navigation -->
      <v-tabs v-model="activeTab" class="bg-surface" hide-slider>
        <v-tab value="details">{{ $t('common.details') }}</v-tab>
        <v-tab value="attributes">{{ $t('common.attributes') }}</v-tab>
      </v-tabs>

      <!-- Tab Content -->
      <v-window v-model="activeTab" class="transparent">
        <!-- Details Tab -->
        <v-window-item value="details" style="padding: 24px;">
          <v-form ref="formRef" @submit.prevent="handleSave">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="asset.title"
                  :label="$t('asset.title')"
                  :rules="[requiredRule]"
                  :disabled="!canModify"
                  @blur="handleUpdateRecord"
                />
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="asset.description"
                  :label="$t('asset.description')"
                  :disabled="!canModify"
                  rows="4"
                  @blur="handleUpdateRecord"
                />
              </v-col>
            </v-row>

            <!-- Action Buttons -->
            <v-row class="mt-4">
              <v-col cols="12" md="6">
                <v-btn
                  prepend-icon="mdi-content-save"
                  variant="outlined"
                  :disabled="!canModify"
                  @click="handleSave"
                >
                  {{ $t('common.save') }}
                </v-btn>
              </v-col>
              <v-col cols="12" md="6">
                <v-btn prepend-icon="mdi-close" variant="outlined" @click="handleCancel">
                  {{ $t('common.cancel') }}
                </v-btn>
              </v-col>
            </v-row>

            <!-- Error Messages -->
            <v-row v-if="showError" class="mt-4">
              <v-col cols="12">
                <v-alert type="error" variant="tonal">
                  {{ $t('asset.error') }}
                </v-alert>
              </v-col>
            </v-row>
          </v-form>
        </v-window-item>

        <!-- Attributes Tab -->
        <v-window-item value="attributes" style="padding: 24px;">
          <v-row>
            <v-col v-if="assetAttributes.length === 0" cols="12" class="text-center text-grey">
              {{ $t('common.no_data') }}
            </v-col>
            <v-col v-for="attributeItem in assetAttributes" :key="attributeItem.id" cols="12">
              <AttributeContainer
                :attribute-item="attributeItem"
                :report-item-id="asset.id || 0"
                :read-only="!canModify"
                @attribute-updated="handleAttributeUpdated"
              />
            </v-col>
          </v-row>
        </v-window-item>
      </v-window>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'

const { t } = useI18n()
const { checkPermission } = useAuth()

// Component state
const visible = ref(false)
const showError = ref(false)
const showCloseConfirmation = ref(false)
const activeTab = ref('details')
const formRef = ref(null)
const canModifyFlag = ref(false)
const initialFormState = ref(null)

// Form data
const asset = ref({
  id: 0,
  title: '',
  description: ''
})

const assetAttributes = ref([])

// Validation rules
const requiredRule = (value) => !!value || t('common.required')

// Computed properties
const canModify = computed(() => checkPermission('MY_ASSETS_CREATE') && canModifyFlag.value)

// Methods
function resetForm() {
  asset.value = {
    id: 0,
    title: '',
    description: ''
  }
  showError.value = false
  canModifyFlag.value = false
  activeTab.value = 'details'
  assetAttributes.value = []
  formRef.value?.reset()
  initialFormState.value = snapshotForm()
}

function snapshotForm() {
  return JSON.stringify({
    asset: asset.value
  })
}

function hasUnsavedChanges() {
  if (initialFormState.value === null) return false
  return snapshotForm() !== initialFormState.value
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  try {
    // TODO: Implement actual save/update API call
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'asset.updated_successfully' }
      })
    )
    window.dispatchEvent(new CustomEvent('asset-updated'))
    initialFormState.value = snapshotForm()
  } catch (error) {
    showError.value = true
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'asset.error' }
      })
    )
  }
}

async function handleUpdateRecord() {
  if (asset.value.id === 0) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  try {
    // TODO: Implement actual update API call
    window.dispatchEvent(new CustomEvent('asset-updated'))
    initialFormState.value = snapshotForm()
  } catch (error) {
    showError.value = true
  }
}

function handleCancel() {
  if (hasUnsavedChanges()) {
    showCloseConfirmation.value = true
    return
  }
  closeDialog()
}

function confirmClose() {
  showCloseConfirmation.value = false
  closeDialog()
}

function closeDialog() {
  visible.value = false
  resetForm()
}

function handleAttributeUpdated(updatedAttribute) {
  const index = assetAttributes.value.findIndex((a) => a.id === updatedAttribute.id)
  if (index !== -1) {
    assetAttributes.value[index] = updatedAttribute
  }
}

async function loadAssetAttributes() {
  try {
    // TODO: Implement API endpoint to fetch asset attributes
    // const response = await getAssetAttributes(asset.value.id)
    // assetAttributes.value = response.data.attributes || []
    assetAttributes.value = []
  } catch (error) {
    console.error('Failed to load asset attributes:', error)
    assetAttributes.value = []
  }
}

// Public methods
function openDialog(data) {
  visible.value = true
  canModifyFlag.value = data?.modify || true
  showError.value = false

  asset.value = {
    id: data?.id || 0,
    title: data?.title || '',
    description: data?.description || ''
  }

  if (asset.value.id > 0) {
    loadAssetAttributes()
  }

  initialFormState.value = snapshotForm()
}

// Lifecycle
onMounted(() => {
  window.addEventListener('show-asset-edit', (event) => {
    openDialog(event.detail)
  })
})

onUnmounted(() => {
  window.removeEventListener('show-asset-edit', (event) => {
    openDialog(event.detail)
  })
})

// Expose methods
defineExpose({
  openDialog
})
</script>

<style scoped>
.v-toolbar :deep(.v-select) {
  margin-top: 8px;
}
</style>
