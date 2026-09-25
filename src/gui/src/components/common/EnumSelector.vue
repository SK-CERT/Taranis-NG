<template>
    <v-tooltip :text="t('report_item.tooltip.enum_selector')">
        <template #activator="{ props: tooltipProps }">
            <v-btn
                v-bind="tooltipProps"
                class="enum-selector__activator"
                icon="mdi-feature-search-outline"
                size="small"
                variant="tonal"
                :disabled="disabled"
                :aria-label="t('report_item.tooltip.enum_selector')"
                @click="open"
            />
        </template>
    </v-tooltip>

    <v-dialog
        v-model="visible"
        max-width="960"
        scrollable
    >
        <v-card class="enum-selector">
            <v-toolbar
                color="primary"
                density="comfortable"
            >
                <v-toolbar-title>{{ t('attribute.select_enum') }}</v-toolbar-title>
                <v-spacer />
                <v-btn
                    icon="mdi-close"
                    :aria-label="t('notification.close')"
                    @click="close"
                />
            </v-toolbar>

            <v-card-text class="enum-selector__content">
                <v-text-field
                    v-model="search"
                    class="enum-selector__search"
                    prepend-inner-icon="mdi-magnify"
                    :label="t('attribute.search')"
                    variant="outlined"
                    density="compact"
                    clearable
                    hide-details
                    autofocus
                />

                <v-alert
                    v-if="loadError"
                    type="error"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                >
                    {{ t('common.error') }}
                </v-alert>

                <v-data-table-server
                    v-model:page="page"
                    v-model:items-per-page="itemsPerPage"
                    class="enum-selector__table"
                    :headers="headers"
                    :items="items"
                    :items-length="totalCount"
                    :loading="loading"
                    :items-per-page-options="[25, 50, 100]"
                    item-value="value"
                    hover
                    @update:options="updateOptions"
                    @click:row="selectRow"
                >
                    <template #item.value="{ item }">
                        <code>{{ displayValue(item.value) }}</code>
                    </template>
                    <template #no-data>
                        {{ t('common.no_data') }}
                    </template>
                </v-data-table-server>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, onUnmounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { getAttributeEnums } from '@/api/analyze'
    import { getCPEAttributeEnums } from '@/api/assets'

    type EnumItem = {
        value: unknown
        description?: string | null
        [key: string]: unknown
    }

    type EnumResponse = {
        data?: {
            items?: EnumItem[]
            total_count?: number
        }
    }

    type TableOptions = {
        page: number
        itemsPerPage: number
    }

    const props = withDefaults(
        defineProps<{
            attributeId: string | number | undefined
            valueIndex: number
            cpeOnly?: boolean
            disabled?: boolean
        }>(),
        {
            cpeOnly: false,
            disabled: false
        }
    )

    const emit = defineEmits<{
        (event: 'enum-selected', data: { index: number; value: unknown; value_description?: string }): void
    }>()

    const { t } = useI18n()
    const visible = ref(false)
    const loading = ref(false)
    const loadError = ref(false)
    const search = ref('')
    const page = ref(1)
    const itemsPerPage = ref(25)
    const items = ref<EnumItem[]>([])
    const totalCount = ref(0)
    let searchTimer: ReturnType<typeof setTimeout> | null = null
    let requestSequence = 0

    const headers = computed(() => [
        { title: t('attribute.value'), key: 'value', sortable: false },
        { title: t('attribute.description'), key: 'description', sortable: false }
    ])

    const displayValue = (value: unknown): string => {
        const text = String(value ?? '')
        return props.cpeOnly ? text.replaceAll('%', '*') : text
    }

    const loadItems = async (): Promise<void> => {
        if (!props.cpeOnly && props.attributeId === undefined) {
            items.value = []
            totalCount.value = 0
            return
        }

        const sequence = ++requestSequence
        loading.value = true
        loadError.value = false

        const filter = {
            search: search.value || '',
            offset: (page.value - 1) * itemsPerPage.value,
            limit: itemsPerPage.value
        }

        try {
            const response = (
                props.cpeOnly ? await getCPEAttributeEnums(filter) : await getAttributeEnums({ ...filter, attribute_id: props.attributeId })
            ) as EnumResponse

            if (sequence !== requestSequence) return
            items.value = Array.isArray(response.data?.items) ? response.data.items : []
            totalCount.value = Number(response.data?.total_count ?? 0)
        } catch {
            if (sequence !== requestSequence) return
            items.value = []
            totalCount.value = 0
            loadError.value = true
        } finally {
            if (sequence === requestSequence) loading.value = false
        }
    }

    const open = (): void => {
        if (props.disabled) return
        page.value = 1
        visible.value = true
        void loadItems()
    }

    const close = (): void => {
        visible.value = false
    }

    const updateOptions = (options: TableOptions): void => {
        if (!visible.value) return
        const changed = page.value !== options.page || itemsPerPage.value !== options.itemsPerPage
        page.value = options.page
        itemsPerPage.value = options.itemsPerPage
        if (changed) void loadItems()
    }

    const select = (item: EnumItem): void => {
        const value = displayValue(item.value)
        const data: { index: number; value: string; value_description?: string } = {
            index: props.valueIndex,
            value
        }
        if (item.description !== undefined && item.description !== null) {
            data.value_description = String(item.description)
        }
        emit('enum-selected', data)
        close()
    }

    const selectRow = (_event: Event, row: { item: EnumItem }): void => {
        select(row.item)
    }

    watch(search, () => {
        if (!visible.value) return
        if (searchTimer) clearTimeout(searchTimer)
        searchTimer = setTimeout(() => {
            page.value = 1
            void loadItems()
        }, 300)
    })

    onUnmounted(() => {
        requestSequence += 1
        if (searchTimer) clearTimeout(searchTimer)
    })

    defineExpose({ open, close, loadItems, select, search, page, itemsPerPage, updateOptions })
</script>

<style scoped>
    .enum-selector__activator {
        border: 1px solid rgba(var(--v-theme-primary), 0.34);
    }

    .enum-selector {
        border: 1px solid rgba(var(--v-theme-outline), 0.55);
        background: rgb(var(--v-theme-surface));
    }

    .enum-selector__content {
        padding: 1rem;
        background: rgb(var(--v-theme-background));
    }

    .enum-selector__search {
        margin-bottom: 0.9rem;
    }

    .enum-selector__table {
        overflow: hidden;
        border: 1px solid rgba(var(--v-theme-outline), 0.48);
        border-radius: 4px;
        background: rgb(var(--v-theme-surface));
    }

    .enum-selector__table :deep(tbody tr) {
        cursor: pointer;
    }

    .enum-selector__table code {
        color: rgb(var(--v-theme-on-surface));
        background: transparent;
    }
</style>
