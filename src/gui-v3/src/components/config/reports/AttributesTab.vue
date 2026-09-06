<template>
    <v-container fluid>
        <v-card>
            <!-- Toolbar -->
            <v-card-text>
                <v-row>
                    <v-col cols="8">
                        <SearchField
                            v-model="search"
                            :width="350"
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-end"
                    >
                        <NewAttribute
                            :edit-item="editItem"
                            @saved="handleSaved"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table
                ref="tableRef"
                v-model:items-per-page="itemsPerPage"
                :headers="headers"
                :items="configStore.attributes.items"
                :search="search"
                :loading="loading"
                item-key="id"
                class="elevation-1 auto-paged"
            >
                <template #item.name="{ item }">
                    <v-icon
                        :icon="typeIcon(asAttributeItem(item).type)"
                        size="small"
                        class="me-2 text-medium-emphasis"
                    />
                    <strong>{{ asAttributeItem(item).name }}</strong>
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="me-1"
                        @click="handleEdit(asAttributeItem(item))"
                    />
                    <ActionButton
                        v-if="canDelete"
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asAttributeItem(item))"
                    />
                </template>
            </v-data-table>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
    import { computed, ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteAttribute } from '@/api/config'
    import { ICONS } from '@/config/ui-constants'
    import NewAttribute from '@/components/config/reports/NewAttribute.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useAutoItemsPerPage } from '@/composables/useAutoItemsPerPage'

    // Representative icon per attribute type.
    const TYPE_ICONS: Record<string, string> = {
        STRING: 'mdi-format-text',
        NUMBER: 'mdi-numeric',
        BOOLEAN: 'mdi-toggle-switch-outline',
        DATE: 'mdi-calendar',
        TIME: 'mdi-clock-outline',
        DATE_TIME: 'mdi-calendar-clock',
        TEXT: 'mdi-text-long',
        RICH_TEXT: 'mdi-text-box-outline',
        ENUM: 'mdi-format-list-bulleted',
        RADIO: 'mdi-radiobox-marked',
        MULTI_CHOICE: 'mdi-checkbox-multiple-marked-outline',
        CVSS: 'mdi-calculator',
        CPE: 'mdi-laptop',
        CVE: 'mdi-bug-outline',
        CWE: 'mdi-shield-alert-outline',
        TLP: 'mdi-traffic-light',
        ATTACHMENT: 'mdi-paperclip'
    }
    const typeIcon = (type?: string): string => (type && TYPE_ICONS[type]) || ICONS.FILE_DOCUMENT

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    type AttributeItem = {
        id: string | number
        name?: string
        description?: string
        type?: string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()
    const canDelete = computed(() => checkPermission('CONFIG_ATTRIBUTE_DELETE'))

    const search = ref('')
    const loading = ref(false)
    const editItem = ref<AttributeItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('reports.attributes.name'), key: 'name' },
        { title: t('reports.attributes.type'), key: 'type' },
        { title: t('reports.attributes.description'), key: 'description' },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const asAttributeItem = (item: unknown): AttributeItem => item as AttributeItem

    // The page holds as many rows as the viewport fits, so the footer's page-size select is
    // hidden (see the scoped style below) - there is nothing left for it to choose.
    const tableRef = ref<{ $el?: HTMLElement } | null>(null)
    const { itemsPerPage, recalculate } = useAutoItemsPerPage(tableRef)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadAttributes({ search: '' })
        } catch (error) {
            console.error('Error loading attributes:', error)
        } finally {
            loading.value = false
        }
        // Rows only exist to measure once the data has rendered.
        await nextTick()
        recalculate()
    }

    const handleEdit = async (item: AttributeItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog.
        editItem.value = null
        await nextTick()
        editItem.value = item
    }

    const handleDelete = async (item: AttributeItem): Promise<void> => {
        if (!canDelete.value) return
        try {
            await deleteAttribute(item)
            await loadData()
        } catch (error) {
            console.error('Error deleting attribute:', error)
            // The backend refuses to delete an attribute that report types still build fields
            // on, and names them. Say so instead of leaving the row silently undeleted.
            const data = (error as { response?: { data?: { report_types?: string[]; error?: string } } })?.response?.data
            const detail = data?.report_types?.length
                ? { type: 'error', loc: 'reports.attributes.in_use', params: { types: data.report_types.join(', ') } }
                : { type: 'error', loc: 'common.error_deleting' }
            window.dispatchEvent(new CustomEvent('notification', { detail }))
        }
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(loadData)
</script>

<style scoped>
    /* The page size is computed from the viewport, so the footer's selector is redundant. */
    .auto-paged :deep(.v-data-table-footer__items-per-page) {
        display: none;
    }
</style>
