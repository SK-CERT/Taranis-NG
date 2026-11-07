<template>
    <v-dialog
        v-model="dialog"
        max-width="1000"
        persistent
        scrollable
        @keydown.esc.stop="requestClose"
        @after-leave="resetFormState"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
                @click="openCreateDialog"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('product_presets.edit') : t('product_presets.add_new')"
                :saving="saving"
                :show-save="canSave"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    :disabled="!canSave"
                    validate-on="submit"
                    @submit.prevent="saveAndClose"
                >
                    <div class="d-flex align-start ga-3 mb-3">
                        <MdiIconPicker
                            v-model="iconModel"
                            :label="t('product_presets.icon')"
                            :disabled="saving || !canSave"
                            hide-label
                            class="name-icon"
                            data-test="product-preset-icon"
                        />
                        <v-text-field
                            v-model="localItem.name"
                            dir="auto"
                            :spellcheck="spellcheck"
                            :label="t('product_presets.name')"
                            variant="outlined"
                            density="comfortable"
                            :rules="[required]"
                            :disabled="saving"
                        />
                    </div>

                    <v-textarea
                        v-model="localItem.description"
                        dir="auto"
                        :spellcheck="spellcheck"
                        :label="t('product_presets.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="2"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <div class="text-title-medium">{{ t('product_presets.deliveries') }}</div>
                    <div class="text-body-2 text-medium-emphasis mb-3">{{ t('product_presets.deliveries_hint') }}</div>

                    <div
                        v-for="(row, index) in rows"
                        :key="row.uid"
                        class="product-preset-row"
                        data-test="product-preset-row"
                    >
                        <!-- The fields may wrap on a narrow screen; the row's buttons stay beside them. -->
                        <div class="product-preset-row__fields">
                            <v-select
                                v-model="row.language"
                                dir="auto"
                                :items="languageItems"
                                item-title="title"
                                item-value="value"
                                :label="t('product_presets.language')"
                                variant="outlined"
                                density="comfortable"
                                class="product-preset-row__language"
                                data-test="delivery-language"
                                :disabled="saving"
                            />
                            <v-select
                                v-model="row.product_format_id"
                                dir="auto"
                                :items="formatItemsFor(row)"
                                item-title="title"
                                item-value="id"
                                :label="t('product_presets.format')"
                                variant="outlined"
                                density="comfortable"
                                class="product-preset-row__format"
                                :rules="[required]"
                                :disabled="saving"
                            />
                            <v-select
                                v-model="row.channel_ids"
                                dir="auto"
                                :items="options.channels"
                                item-title="name"
                                item-value="id"
                                :label="t('product_presets.channels')"
                                :placeholder="t('product_presets.format_only')"
                                persistent-placeholder
                                multiple
                                chips
                                closable-chips
                                variant="outlined"
                                density="comfortable"
                                class="product-preset-row__channels"
                                :disabled="saving"
                            />
                        </div>
                        <div class="product-preset-row__actions">
                            <v-btn
                                icon="mdi-arrow-up"
                                variant="text"
                                size="small"
                                :title="t('product_presets.move_up')"
                                :disabled="saving || !canSave || index === 0"
                                @click="moveRow(index, -1)"
                            />
                            <v-btn
                                icon="mdi-arrow-down"
                                variant="text"
                                size="small"
                                :title="t('product_presets.move_down')"
                                :disabled="saving || !canSave || index === rows.length - 1"
                                @click="moveRow(index, 1)"
                            />
                            <v-btn
                                icon="mdi-delete-outline"
                                variant="text"
                                size="small"
                                :title="t('product_presets.remove_format')"
                                :disabled="saving || !canSave"
                                @click="removeRow(index)"
                            />
                        </div>
                    </div>

                    <v-btn
                        v-if="canSave"
                        prepend-icon="mdi-plus"
                        variant="tonal"
                        color="primary"
                        class="mb-4"
                        :disabled="saving || options.formats.length === 0"
                        data-test="add-format"
                        @click="addRow"
                    >
                        {{ t('product_presets.add_format') }}
                    </v-btn>

                    <v-divider class="my-4" />

                    <div class="text-title-medium mb-2">{{ t('product_presets.public_web') }}</div>
                    <v-switch
                        v-model="localItem.public_web_enabled"
                        :label="t('product_presets.public_web_enabled')"
                        color="primary"
                        hide-details
                        class="mb-2"
                        :disabled="saving"
                    />
                    <v-select
                        v-if="localItem.public_web_enabled && options.public_webs.length > 0"
                        v-model="localItem.public_web_ids"
                        dir="auto"
                        :items="options.public_webs"
                        item-title="name"
                        item-value="id"
                        :label="t('product_presets.public_web_ids')"
                        :hint="t('product_presets.public_web_ids_hint')"
                        persistent-hint
                        multiple
                        chips
                        closable-chips
                        variant="outlined"
                        density="comfortable"
                        :disabled="saving"
                    />
                </v-form>

                <v-alert
                    v-if="showNeedsDelivery"
                    type="warning"
                    variant="tonal"
                    class="mt-4"
                >
                    {{ t('product_presets.needs_delivery') }}
                </v-alert>

                <v-alert
                    v-if="errorDetail !== null"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="errorDetail = null"
                >
                    <div>{{ t('product_presets.error') }}</div>
                    <div
                        v-if="errorDetail"
                        class="text-body-2"
                    >
                        <bdi dir="auto">{{ errorDetail }}</bdi>
                    </div>
                </v-alert>
            </v-card-text>
        </v-card>

        <UnsavedChangesDialog
            v-model="confirmVisible"
            @continue="continueEditing"
            @save="saveAndClose"
            @discard="discardAndClose"
        />
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { useAuth } from '@/composables/useAuth'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import MdiIconPicker from '@/components/common/MdiIconPicker.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { createProductPreset, updateProductPreset, getProductPresetOptions } from '@/api/config'
    import {
        DEFAULT_PRODUCT_ICON,
        deliveriesToRows,
        newFormatRow,
        OWN_LANGUAGE,
        rowsToDeliveries,
        type ProductPreset,
        type ProductPresetFormatRow,
        type ProductPresetOptions
    } from '@/types/product-presets'

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<ProductPreset> | null
        }>(),
        {
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'saved'): void
    }>()

    const { t } = useI18n()
    const spellcheck = useSpellcheck()
    const { checkPermission } = useAuth()
    const { languageOptions, languageName } = useContentLanguages()

    const emptyItem = (): ProductPreset => ({
        id: null,
        name: '',
        description: '',
        icon: null,
        deliveries: [],
        public_web_enabled: false,
        public_web_ids: []
    })

    const dialog = ref(false)
    const saving = ref(false)
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }>; resetValidation?: () => void } | null>(null)
    const localItem = ref<ProductPreset>(emptyItem())
    const rows = ref<ProductPresetFormatRow[]>([])
    const options = ref<ProductPresetOptions>({ formats: [], channels: [], public_webs: [] })
    const showNeedsDelivery = ref(false)
    // null: no error; '' : an error without details; otherwise what the server said.
    const errorDetail = ref<string | null>(null)

    const isEdit = computed(() => localItem.value.id !== null && localItem.value.id !== undefined && localItem.value.id !== -1)
    const canCreate = computed(() => checkPermission('CONFIG_PRODUCT_PRESET_CREATE'))
    const canSave = computed(() => checkPermission(isEdit.value ? 'CONFIG_PRODUCT_PRESET_UPDATE' : 'CONFIG_PRODUCT_PRESET_CREATE'))

    // The picker shows the default icon of a product preset without its own; it is stored only once picked.
    const iconModel = computed({
        get: () => localItem.value.icon || DEFAULT_PRODUCT_ICON,
        set: (icon: string) => {
            localItem.value.icon = icon
        }
    })

    const required = (value: unknown): true | string => (value !== null && value !== undefined && value !== '') || t('error.required')

    // The product's own language, then the content languages, and any other a row already has.
    const languageItems = computed(() => {
        const items = [
            { title: t('product_presets.own_language'), value: OWN_LANGUAGE },
            ...languageOptions.value.map((option) => ({ title: option.txt, value: option.id }))
        ]
        for (const row of rows.value) {
            if (!items.some((item) => item.value === row.language)) items.push({ title: languageName(row.language), value: row.language })
        }
        return items
    })

    // One row per language and format: a row offers the formats no other row of its language has taken.
    const formatItemsFor = (row: ProductPresetFormatRow) => {
        const taken = new Set(
            rows.value.filter((other) => other !== row && other.language === row.language).map((other) => other.product_format_id)
        )
        return options.value.formats.filter((format) => !taken.has(format.id))
    }

    function addRow(): void {
        rows.value.push(newFormatRow())
    }

    function removeRow(index: number): void {
        rows.value.splice(index, 1)
    }

    function moveRow(index: number, offset: number): void {
        const target = index + offset
        if (target < 0 || target >= rows.value.length) return
        const [moved] = rows.value.splice(index, 1)
        if (moved) rows.value.splice(target, 0, moved)
    }

    function openCreateDialog(): void {
        localItem.value = emptyItem()
        rows.value = [newFormatRow()]
        showNeedsDelivery.value = false
        errorDetail.value = null
    }

    function resetFormState(): void {
        localItem.value = emptyItem()
        rows.value = []
        showNeedsDelivery.value = false
        errorDetail.value = null
        saving.value = false
        formRef.value?.resetValidation?.()
    }

    async function loadOptions(): Promise<void> {
        try {
            const response = (await getProductPresetOptions()) as { data?: Partial<ProductPresetOptions> }
            options.value = {
                formats: response.data?.formats || [],
                channels: response.data?.channels || [],
                public_webs: response.data?.public_webs || []
            }
        } catch (error) {
            console.error('Error loading product preset options:', error)
        }
    }

    const serverError = (error: unknown): string => {
        const message = (error as { response?: { data?: { error?: unknown } } }).response?.data?.error
        return typeof message === 'string' ? message : ''
    }

    // Persists the form. Returns true on success so the guard can decide whether to close.
    async function persist(): Promise<boolean> {
        if (!canSave.value) return false
        errorDetail.value = null
        showNeedsDelivery.value = false

        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return false

        const deliveries = rowsToDeliveries(rows.value)
        if (deliveries.length === 0 && !localItem.value.public_web_enabled) {
            showNeedsDelivery.value = true
            return false
        }

        saving.value = true
        try {
            const payload = {
                ...localItem.value,
                deliveries,
                // A web list only means something while the public web is on.
                public_web_ids: localItem.value.public_web_enabled ? localItem.value.public_web_ids : []
            }
            if (isEdit.value) {
                await updateProductPreset(payload)
            } else {
                await createProductPreset({ ...payload, id: -1 })
            }
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: isEdit.value ? 'product_presets.successful_edit' : 'product_presets.successful' }
                })
            )
            emit('saved')
            return true
        } catch (error) {
            errorDetail.value = serverError(error)
            return false
        } finally {
            saving.value = false
        }
    }

    function closeDialog(): void {
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({
            item: { ...localItem.value, deliveries: undefined },
            deliveries: rowsToDeliveries(rows.value)
        }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = {
                    ...emptyItem(),
                    ...newItem,
                    description: newItem.description || '',
                    public_web_ids: [...(newItem.public_web_ids || [])]
                } as ProductPreset
                rows.value = deliveriesToRows(newItem.deliveries || [])
                showNeedsDelivery.value = false
                errorDetail.value = null
                dialog.value = true
            }
        },
        { immediate: true, deep: true }
    )

    watch(dialog, (open) => {
        if (open) {
            // Snapshot the freshly-loaded form as the clean baseline for dirty-tracking.
            capture()
        }
    })

    onMounted(loadOptions)
</script>

<style scoped>
    .name-icon {
        flex: 0 0 96px;
    }

    .product-preset-row {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 4px;
    }

    .product-preset-row__fields {
        display: flex;
        flex: 1 1 auto;
        flex-wrap: wrap;
        gap: 8px;
        min-width: 0;
    }

    .product-preset-row__language {
        flex: 1 1 180px;
    }

    .product-preset-row__format {
        flex: 1 1 220px;
    }

    .product-preset-row__channels {
        flex: 2 1 320px;
    }

    .product-preset-row__actions {
        display: flex;
        flex: 0 0 auto;
        padding-top: 6px;
    }
</style>
