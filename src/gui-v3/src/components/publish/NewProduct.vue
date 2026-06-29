<template>
    <v-dialog
        v-model="visible"
        fullscreen
        persistent
        @keydown.esc="handleCancel"
    >
        <!-- Confirmation dialogs -->
        <v-dialog
            v-model="showCloseConfirmation"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ $t('confirm_close.title') }}
                </v-card-title>
                <v-card-text>{{ $t('product.confirm_close.message') }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        color="primary"
                        variant="elevated"
                        class="confirm-btn"
                        @click="showCloseConfirmation = false"
                    >
                        {{ $t('confirm_close.continue') }}
                    </v-btn>
                    <v-btn
                        color="success"
                        variant="elevated"
                        class="confirm-btn"
                        @click="saveAndClose"
                    >
                        {{ $t('confirm_close.save_and_close') }}
                    </v-btn>
                    <v-btn
                        color="error"
                        variant="elevated"
                        class="confirm-btn"
                        @click="confirmClose"
                    >
                        {{ $t('confirm_close.close') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog
            v-model="showPublishConfirmation"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ $t('product.publish_confirmation') }}
                </v-card-title>
                <v-card-text>{{ product.title }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn @click="showPublishConfirmation = false">
                        {{ $t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        @click="handlePublish"
                    >
                        {{ $t('common.yes') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog
            v-model="showPublishUnsavedConfirmation"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ $t('product.publish_unsaved.title') }}
                </v-card-title>
                <v-card-text>{{ $t('product.publish_unsaved.message') }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn @click="showPublishUnsavedConfirmation = false">
                        {{ $t('product.publish_unsaved.close') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        @click="saveAndPublish"
                    >
                        {{ $t('product.publish_unsaved.save_and_publish') }}
                    </v-btn>
                    <v-btn
                        color="error"
                        @click="publishOnly"
                    >
                        {{ $t('product.publish_unsaved.publish_only') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Main dialog -->
        <v-card class="d-flex flex-column h-100">
            <v-toolbar
                color="primary"
                dark
            >
                <v-btn
                    icon
                    @click="handleCancel"
                >
                    <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
                </v-btn>
                <v-toolbar-title>
                    {{ isEditMode ? $t('product.edit') : $t('product.add_new') }}
                </v-toolbar-title>
                <v-spacer />
                <StateSelector
                    v-if="availableStates.length > 0"
                    :model-value="product.state_id ?? ''"
                    :available-states="availableStates"
                    :label="$t('product.state')"
                    :disabled="!canModify"
                    class="me-4"
                    @update:model-value="handleStateChange"
                />
                <v-btn
                    v-if="!isEditMode && canModify && product.id === -1"
                    text
                    @click="handleSave"
                >
                    <v-icon start>
                        {{ ICONS.CONTENT_SAVE }}
                    </v-icon>
                    {{ $t('common.save') }}
                </v-btn>
            </v-toolbar>

            <v-card-text class="pa-4 overflow-y-auto bg-background">
                <v-form
                    ref="formRef"
                    @submit.prevent="handleSave"
                >
                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                        >
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
                        <v-col
                            cols="12"
                            md="6"
                        >
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
                                color="primary"
                                variant="flat"
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
                            <div class="text-title-medium mb-2">
                                {{ $t('product.publisher_presets') }}
                            </div>
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
                            <div
                                v-else
                                class="text-center text-grey py-4"
                            >
                                {{ $t('common.no_data') }}
                            </div>
                        </v-col>
                    </v-row>

                    <!-- Action Buttons -->
                    <v-row class="mt-4">
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-btn
                                :prepend-icon="ICONS.READ_OUTLINE"
                                color="primary"
                                variant="flat"
                                @click="handlePreview"
                            >
                                {{ $t('product.preview') }}
                            </v-btn>
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-btn
                                v-if="canPublish"
                                :prepend-icon="ICONS.SEND_OUTLINE"
                                color="primary"
                                variant="flat"
                                @click="handlePublishConfirmation"
                            >
                                {{ $t('product.publish') }}
                            </v-btn>
                        </v-col>
                    </v-row>

                    <!-- Error Messages -->
                    <v-row v-if="showError">
                        <v-col cols="12">
                            <v-alert
                                type="error"
                                variant="tonal"
                            >
                                {{ $t('product.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
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

    type ProductModel = {
        id: number
        title: string
        description: string
        product_type_id: number | string | undefined
        state_id: number | string | undefined
        report_items: Array<{ id: number | string }>
    }

    type FormRef = {
        reset?: () => void
        validate?: () => Promise<{ valid: boolean }>
    }

    type ReportItem = {
        id: number | string
        [key: string]: unknown
    }

    type PublisherPreset = {
        id: number | string
        name: string
        selected: boolean
        [key: string]: unknown
    }

    type AvailableState = {
        id: number | string
        title?: string
        is_default?: boolean
        [key: string]: unknown
    }

    type ProductType = {
        id: number | string
        title?: string
        [key: string]: unknown
    }

    type ProductEditPayload = {
        id: number
        title: string
        description: string
        product_type_id: number | string | undefined
        state_id: number | string | undefined
        report_items?: ReportItem[]
        modify: boolean
        access: boolean
    }

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const authStore = useAuthStore()

    // Component state
    const visible = ref<boolean>(false)
    const isEditMode = ref<boolean>(false)
    const showError = ref<boolean>(false)
    const showCloseConfirmation = ref<boolean>(false)
    const showPublishConfirmation = ref<boolean>(false)
    const showPublishUnsavedConfirmation = ref<boolean>(false)
    const initialFormState = ref<string | null>(null)
    const formRef = ref<FormRef | null>(null)
    const canModifyFlag = ref<boolean>(false)
    const canAccessFlag = ref<boolean>(false)

    // Form data
    const product = ref<ProductModel>({
        id: -1,
        title: '',
        description: '',
        product_type_id: undefined,
        state_id: undefined,
        report_items: []
    })

    const selectedType = ref<ProductType | null>(null)
    const reportItems = ref<ReportItem[]>([])
    const productTypes = ref<ProductType[]>([])
    const publisherPresets = ref<PublisherPreset[]>([])
    const availableStates = ref<AvailableState[]>([])
    const reportItemSelector = ref<{ openSelector?: () => void } | null>(null)

    // Validation rules
    const requiredRule = (value: string | number | null | undefined): true | string => !!value || t('common.required')

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
            product_type_id: undefined,
            state_id: undefined,
            report_items: []
        }
        selectedType.value = null
        isEditMode.value = false
        showError.value = false
        canModifyFlag.value = false
        canAccessFlag.value = false
        reportItems.value = []
        formRef.value?.reset?.()
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

    function handleProductTypeChange(): void {
        if (selectedType.value) {
            product.value.product_type_id = selectedType.value.id
            handleUpdateRecord()
        }
    }

    function prepareProduct(): void {
        showError.value = false
        product.value.product_type_id = selectedType.value?.id
        product.value.report_items = reportItems.value.map((item) => ({ id: item.id }))
    }

    function openReportItemSelector(): void {
        reportItemSelector.value?.openSelector?.()
    }

    async function handleReportItemsChanged(items: ReportItem[]): Promise<void> {
        reportItems.value = Array.isArray(items) ? [...items] : []

        if (isEditMode.value && product.value.id !== -1) {
            await handleUpdateRecord()
        }
    }

    function getSelectedPublisherIds(): Array<number | string> {
        return publisherPresets.value.filter((preset) => preset.selected).map((preset) => preset.id)
    }

    function validatePublisherSelection(): boolean {
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

    async function handleSave(): Promise<boolean> {
        const validate = formRef.value?.validate
        if (!validate) {
            return false
        }
        const { valid } = (await validate()) || { valid: false }
        if (!valid) return false

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
            return true
        } catch {
            showError.value = true
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.error' }
                })
            )
            return false
        }
    }

    function handleStateChange(newStateId: number | string | null): void {
        // StateSelector is bound one-way via :model-value, so we must write the
        // selected id back into the product before persisting.
        product.value.state_id = newStateId ?? undefined
        handleUpdateRecord()
    }

    async function handleUpdateRecord(): Promise<void> {
        if (!isEditMode.value || product.value.id === -1) return

        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return

        prepareProduct()

        try {
            await updateProduct(product.value)
            window.dispatchEvent(new CustomEvent('product-updated'))
            initialFormState.value = snapshotForm()
        } catch {
            showError.value = true
        }
    }

    function handleCancel(): void {
        if (!isEditMode.value && hasUnsavedChanges()) {
            showCloseConfirmation.value = true
            return
        }
        closeDialog()
    }

    function confirmClose(): void {
        showCloseConfirmation.value = false
        closeDialog()
    }

    async function saveAndClose(): Promise<void> {
        showCloseConfirmation.value = false
        const saved = await handleSave()
        if (saved) {
            closeDialog()
        }
    }

    function closeDialog(): void {
        visible.value = false
        resetForm()
    }

    function handlePublishConfirmation(): void {
        if (!validatePublisherSelection()) return

        if (!isEditMode.value && hasUnsavedChanges()) {
            showPublishUnsavedConfirmation.value = true
        } else {
            showPublishConfirmation.value = true
        }
    }

    async function handlePublish(): Promise<void> {
        showPublishConfirmation.value = false

        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
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
        } catch {
            showError.value = true
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.publish_error' }
                })
            )
        }
    }

    async function saveAndPublish(): Promise<void> {
        showPublishUnsavedConfirmation.value = false
        const saved = await handleSave()
        if (saved) {
            isEditMode.value = true
            canModifyFlag.value = true
            canAccessFlag.value = true
            showPublishConfirmation.value = true
        }
    }

    function publishOnly(): void {
        showPublishUnsavedConfirmation.value = false
        handlePublish()
    }

    async function handlePreview(event?: MouseEvent): Promise<void> {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return

        prepareProduct()

        try {
            const ctrl = Boolean(event && event.ctrlKey)
            const response = await previewProduct(product.value, ctrl, authStore.jwt)
            const token = response.data.token

            const apiBase = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || '/api/v1'
            const previewUrl = `${apiBase}/publish/products/preview/${token}`
            // Open the preview URL in a new tab
            window.open(previewUrl, '_blank')
        } catch (error: unknown) {
            console.error('Preview failed:', error)
            showError.value = true
        }
    }

    async function loadAvailableStates() {
        try {
            const response = await getEntityTypeStates('product')
            availableStates.value = response.data.states || []
            selectDefaultState()
        } catch (error: unknown) {
            console.error('Failed to load available states for PRODUCT:', error)
            availableStates.value = []
        }
    }

    async function loadProductTypes() {
        try {
            const response = await getAllUserProductTypes()
            productTypes.value = response.data.items || []
        } catch (error: unknown) {
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
        } catch (error: unknown) {
            console.error('Failed to load publisher presets:', error)
        }
    }

    // Public methods for opening dialog
    function openDialog(): void {
        visible.value = true
        resetForm()
    }

    function openEditDialog(data: ProductEditPayload): void {
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
    const handleNewProduct = (event: Event): void => {
        const data = (event as CustomEvent<unknown>).detail
        openDialog()
        if (data && Array.isArray(data)) {
            reportItems.value = [...(data as ReportItem[])]
        }
    }

    const handleShowProductEdit = (event: Event): void => {
        const data = (event as CustomEvent<unknown>).detail
        if (data && typeof data === 'object') {
            openEditDialog(data as ProductEditPayload)
        }
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

    /* Keep the unsaved-changes dialog button labels white regardless of theme on-* colors. */
    .confirm-btn,
    .confirm-btn :deep(.v-btn__content) {
        color: #fff !important;
    }
</style>
