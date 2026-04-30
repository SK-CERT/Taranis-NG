<template>
  <v-dialog
    v-model="visible"
    fullscreen
    persistent
    @keydown.esc="handleCancel"
  >
    <!-- Confirmation dialogs -->
    <v-dialog v-model="showCloseConfirmation" max-width="500px" persistent>
      <v-card>
        <v-card-title class="text-h5">{{ $t('confirm_close.title') }}</v-card-title>
        <v-card-text>{{ $t('product.confirm_close.message') }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="" @click="showCloseConfirmation = false">
            {{ $t('confirm_close.continue') }}
          </v-btn>
          <v-btn color="primary" @click="saveAndClose">
            {{ $t('confirm_close.save_and_close') }}
          </v-btn>
          <v-btn color="error" @click="confirmClose">
            {{ $t('confirm_close.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showPublishConfirmation" max-width="500px" persistent>
      <v-card>
        <v-card-title class="text-h5">{{ $t('product.publish_confirmation') }}</v-card-title>
        <v-card-text>{{ product.title }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showPublishConfirmation = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" @click="handlePublish">{{ $t('common.yes') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showPublishUnsavedConfirmation" max-width="500px" persistent>
      <v-card>
        <v-card-title class="text-h5">{{ $t('product.publish_unsaved.title') }}</v-card-title>
        <v-card-text>{{ $t('product.publish_unsaved.message') }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showPublishUnsavedConfirmation = false">
            {{ $t('product.publish_unsaved.close') }}
          </v-btn>
          <v-btn color="primary" @click="saveAndPublish">
            {{ $t('product.publish_unsaved.save_and_publish') }}
          </v-btn>
          <v-btn color="error" @click="publishOnly">
            {{ $t('product.publish_unsaved.publish_only') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Main dialog -->
    <v-card class="d-flex flex-column h-100">
      <v-toolbar color="primary" dark>
        <v-btn icon @click="handleCancel">
          <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
        </v-btn>
        <v-toolbar-title>
          {{ isEditMode ? $t('product.edit') : $t('product.add_new') }}
        </v-toolbar-title>
        <v-spacer />
        <StateSelector
          v-if="availableStates.length > 0"
          v-model="product.state_id"
          :available-states="availableStates"
          :label="$t('product.state')"
          :disabled="!canModify"
          @update:model-value="handleUpdateRecord"
        />
        <v-btn v-if="!isEditMode && canModify && product.id === -1" text @click="handleSave">
          <v-icon start>{{ ICONS.CONTENT_SAVE }}</v-icon>
          {{ $t('common.save') }}
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-4 overflow-y-auto">
        <v-form ref="formRef" @submit.prevent="handleSave">
          <v-row>
            <v-col cols="12" md="6">
              <v-combobox
                v-model="selectedType"
                :items="productTypes"
                :item-title="(item) => item?.title || ''"
                :label="$t('product.report_type')"
                :rules="[requiredRule]"
                :disabled="!canModify"
                return-object
                @update:model-value="handleProductTypeChange"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="product.title"
                :label="$t('product.title')"
                :rules="[requiredRule]"
                :disabled="!canModify"
                @blur="handleUpdateRecord"
              />
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="product.description"
                :label="$t('product.description')"
                :disabled="!canModify"
                rows="3"
                @blur="handleUpdateRecord"
              />
            </v-col>
          </v-row>

          <!-- Report Items Section -->
          <v-row>
            <v-col cols="12">
              <v-btn
                v-if="canModify"
                :prepend-icon="ICONS.PLUS"
                variant="outlined"
                class="mb-3"
                @click="openReportItemSelector"
              >
                {{ $t('report_item.select') }}
              </v-btn>

              <ReportItemSelector
                ref="reportItemSelector"
                :values="reportItems"
                :modify="canModify"
                :edit="isEditMode"
                @items-changed="handleReportItemsChanged"
              />
            </v-col>
          </v-row>

          <!-- Publisher Presets -->
          <v-row>
            <v-col cols="12">
              <div class="text-subtitle-2 mb-2">{{ $t('product.publisher_presets') }}</div>
              <div v-if="publisherPresets.length > 0">
                <v-checkbox
                  v-for="preset in publisherPresets"
                  :key="preset.id"
                  v-model="preset.selected"
                  :label="preset.name"
                  :disabled="!canModify"
                  hide-details
                  density="compact"
                />
              </div>
              <div v-else class="text-center text-grey py-4">
                {{ $t('common.no_data') }}
              </div>
            </v-col>
          </v-row>

          <!-- Action Buttons -->
          <v-row class="mt-4">
            <v-col cols="12" md="6">
              <v-btn :prepend-icon="ICONS.READ_OUTLINE" variant="outlined" @click="handlePreview">
                {{ $t('product.preview') }}
              </v-btn>
            </v-col>
            <v-col cols="12" md="6">
              <v-btn
                v-if="canPublish"
                :prepend-icon="ICONS.SEND_OUTLINE"
                variant="outlined"
                color="primary"
                @click="handlePublishConfirmation"
              >
                {{ $t('product.publish') }}
              </v-btn>
            </v-col>
          </v-row>

          <!-- Error Messages -->
          <v-row v-if="showError">
            <v-col cols="12">
              <v-alert type="error" variant="tonal">
                {{ $t('product.error') }}
              </v-alert>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { ICONS } from '@/config/ui-constants'
import { createProduct, updateProduct, publishProduct, previewProduct } from '@/api/publish'
import { getAllUserProductTypes, getAllUserPublishersPresets } from '@/api/user'
import { getEntityTypeStates } from '@/api/state'
import { useAuth } from '@/composables/useAuth'
import StateSelector from '@/components/common/StateSelector.vue'
import ReportItemSelector from '@/components/publish/ReportItemSelector.vue'

const { t } = useI18n()
const { checkPermission } = useAuth()
const authStore = useAuthStore()

// Component state
const visible = ref(false)
const isEditMode = ref(false)
const showError = ref(false)
const showCloseConfirmation = ref(false)
const showPublishConfirmation = ref(false)
const showPublishUnsavedConfirmation = ref(false)
const initialFormState = ref(null)
const formRef = ref(null)
const canModifyFlag = ref(false)
const canAccessFlag = ref(false)

// Form data
const product = ref({
  id: -1,
  title: '',
  description: '',
  product_type_id: null,
  state_id: null,
  report_items: []
})

const selectedType = ref(null)
const reportItems = ref([])
const productTypes = ref([])
const publisherPresets = ref([])
const availableStates = ref([])
const reportItemSelector = ref(null)

// Validation rules
const requiredRule = (value) => !!value || t('common.required')

// Computed properties
const canModify = computed(() => {
  if (!isEditMode.value) return true
  return checkPermission('PUBLISH_UPDATE') && canModifyFlag.value
})

const canPublish = computed(() => {
  if (publisherPresets.value.length === 0) return false
  if (!isEditMode.value) return true
  return checkPermission('PUBLISH_PRODUCT') && canAccessFlag.value
})

// Methods
function resetForm() {
  product.value = {
    id: -1,
    title: '',
    description: '',
    product_type_id: null,
    state_id: null,
    report_items: []
  }
  selectedType.value = null
  isEditMode.value = false
  showError.value = false
  canModifyFlag.value = false
  canAccessFlag.value = false
  reportItems.value = []
  formRef.value?.reset()
  resetPublisherPresets()
  selectDefaultState()
  initialFormState.value = snapshotForm()
}

function resetPublisherPresets() {
  publisherPresets.value.forEach((preset) => {
    preset.selected = false
  })
}

function snapshotForm() {
  return JSON.stringify({
    product: product.value,
    selectedType: selectedType.value,
    reportItems: reportItems.value,
    publisherPresets: publisherPresets.value.map((p) => ({ id: p.id, selected: p.selected }))
  })
}

function hasUnsavedChanges() {
  if (initialFormState.value === null) return false
  return snapshotForm() !== initialFormState.value
}

function selectDefaultState() {
  if (!availableStates.value || availableStates.value.length === 0) return
  const defaultState = availableStates.value.find((state) => state.is_default)
  if (defaultState) {
    product.value.state_id = defaultState.id
  }
}

function handleProductTypeChange() {
  if (selectedType.value) {
    product.value.product_type_id = selectedType.value.id
    handleUpdateRecord()
  }
}

function prepareProduct() {
  showError.value = false
  product.value.product_type_id = selectedType.value?.id || null
  product.value.report_items = reportItems.value.map((item) => ({ id: item.id }))
}

function openReportItemSelector() {
  reportItemSelector.value?.openSelector()
}

async function handleReportItemsChanged(items) {
  reportItems.value = Array.isArray(items) ? [...items] : []

  if (isEditMode.value && product.value.id !== -1) {
    await handleUpdateRecord()
  }
}

function getSelectedPublisherIds() {
  return publisherPresets.value.filter((preset) => preset.selected).map((preset) => preset.id)
}

function validatePublisherSelection() {
  const selectedIds = getSelectedPublisherIds()
  if (selectedIds.length === 0) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'product.no_publisher_selected' }
      })
    )
    return false
  }
  return true
}

async function handleSave() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  prepareProduct()

  try {
    if (product.value.id === -1) {
      const response = await createProduct(product.value)
      product.value.id = response.data
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'product.created_successfully' }
        })
      )
    } else {
      await updateProduct(product.value)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'product.updated_successfully' }
        })
      )
    }
    window.dispatchEvent(new CustomEvent('product-updated'))
    initialFormState.value = snapshotForm()
  } catch (error) {
    showError.value = true
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'product.error' }
      })
    )
  }
}

async function handleUpdateRecord() {
  if (!isEditMode.value || product.value.id === -1) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  prepareProduct()

  try {
    await updateProduct(product.value)
    window.dispatchEvent(new CustomEvent('product-updated'))
    initialFormState.value = snapshotForm()
  } catch (error) {
    showError.value = true
  }
}

function handleCancel() {
  if (!isEditMode.value && hasUnsavedChanges()) {
    showCloseConfirmation.value = true
    return
  }
  closeDialog()
}

function confirmClose() {
  showCloseConfirmation.value = false
  closeDialog()
}

async function saveAndClose() {
  showCloseConfirmation.value = false
  await handleSave()
  if (!showError.value) {
    closeDialog()
  }
}

function closeDialog() {
  visible.value = false
  resetForm()
}

function handlePublishConfirmation() {
  if (!validatePublisherSelection()) return

  if (!isEditMode.value && hasUnsavedChanges()) {
    showPublishUnsavedConfirmation.value = true
  } else {
    showPublishConfirmation.value = true
  }
}

async function handlePublish() {
  showPublishConfirmation.value = false

  const { valid } = await formRef.value.validate()
  if (!valid) return

  prepareProduct()
  const selectedPublisherIds = getSelectedPublisherIds()

  try {
    const response = await publishProduct(product.value, selectedPublisherIds)
    if (response.data.overall_success) {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'product.publish_successful' }
        })
      )
    } else {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'error', loc: 'product.publish_failed' }
        })
      )
    }
  } catch (error) {
    showError.value = true
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'product.publish_error' }
      })
    )
  }
}

async function saveAndPublish() {
  showPublishUnsavedConfirmation.value = false
  await handleSave()
  if (!showError.value) {
    isEditMode.value = true
    canModifyFlag.value = true
    canAccessFlag.value = true
    showPublishConfirmation.value = true
  }
}

function publishOnly() {
  showPublishUnsavedConfirmation.value = false
  handlePublish()
}

async function handlePreview(event) {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  prepareProduct()

  try {
    const ctrl = Boolean(event && event.ctrlKey)
    const response = await previewProduct(product.value, ctrl, authStore.jwt)
    const token = response.data.token

    const apiBase =
      import.meta.env.VITE_APP_TARANIS_NG_CORE_API ||
      window.VUE_APP_TARANIS_NG_CORE_API ||
      '/api/v1'
    const previewUrl = `${apiBase}/publish/products/preview/${token}`

    // hide JWT from URL by creating a form and submitting it as POST, also solve window.open() issue
    const form = document.createElement('form')
    form.method = 'POST'
    form.action = previewUrl
    form.target = '_blank' // open in a new tab - window.open() replacement

    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = 'jwt'
    input.value = authStore.jwt

    form.appendChild(input)
    document.body.appendChild(form)
    form.submit()
    document.body.removeChild(form)
  } catch (error) {
    console.error('Preview failed:', error)
    showError.value = true
  }
}

async function loadAvailableStates() {
  try {
    const response = await getEntityTypeStates('product')
    availableStates.value = response.data.states || []
    selectDefaultState()
  } catch (error) {
    console.error('Failed to load available states for PRODUCT:', error)
    availableStates.value = []
  }
}

async function loadProductTypes() {
  try {
    const response = await getAllUserProductTypes()
    productTypes.value = response.data.items || []
  } catch (error) {
    console.error('Failed to load product types:', error)
  }
}

async function loadPublisherPresets() {
  try {
    const response = await getAllUserPublishersPresets()
    publisherPresets.value = (response.data.items || []).map((preset) => ({
      ...preset,
      selected: false
    }))
  } catch (error) {
    console.error('Failed to load publisher presets:', error)
  }
}

// Public methods for opening dialog
function openDialog() {
  visible.value = true
  resetForm()
}

function openEditDialog(data) {
  visible.value = true
  isEditMode.value = true
  canModifyFlag.value = data.modify
  canAccessFlag.value = data.access
  showError.value = false

  product.value = {
    id: data.id,
    title: data.title,
    description: data.description,
    product_type_id: data.product_type_id,
    state_id: data.state_id,
    report_items: data.report_items || []
  }

  reportItems.value = Array.isArray(data.report_items) ? [...data.report_items] : []
  selectedType.value = productTypes.value.find((type) => type.id === data.product_type_id) || null
  initialFormState.value = snapshotForm()
}

// Event listeners
const handleNewProduct = (event) => {
  const data = event.detail
  openDialog()
  if (data && Array.isArray(data)) {
    reportItems.value = [...data]
  }
}

const handleShowProductEdit = (event) => {
  const data = event.detail
  openEditDialog(data)
}

onMounted(() => {
  loadAvailableStates()
  loadProductTypes()
  loadPublisherPresets()
  window.addEventListener('new-product', handleNewProduct)
  window.addEventListener('show-product-edit', handleShowProductEdit)
})

onUnmounted(() => {
  window.removeEventListener('new-product', handleNewProduct)
  window.removeEventListener('show-product-edit', handleShowProductEdit)
})

// Expose methods for parent components
defineExpose({
  openDialog,
  openEditDialog
})
</script>

<style scoped>
.v-toolbar :deep(.v-select) {
  margin-top: 8px;
}
</style>
