<template>
    <v-container fluid>
        <v-card>
            <v-card-title class="d-flex align-center">
                <span>{{ t('nav_menu.attributes') }}</span>
            </v-card-title>

            <!-- Toolbar -->
            <v-card-text>
                <v-row>
                    <v-col cols="8">
                        <v-text-field
                            v-model="search"
                            :label="t('toolbar_filter.search')"
                            prepend-inner-icon="mdi-magnify"
                            variant="outlined"
                            density="compact"
                            hide-details
                            single-line
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-right"
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
                :headers="headers"
                :items="configStore.attributes.items"
                :search="search"
                :loading="loading"
                item-key="id"
                class="elevation-1"
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
                        class="mr-1"
                        @click="handleEdit(asAttributeItem(item))"
                    />
                    <ActionButton
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
    import { ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteAttribute } from '@/api/config'
    import { ICONS } from '@/config/ui-constants'
    import NewAttribute from '@/components/config/reports/NewAttribute.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'

    // Representative icon per attribute type.
    const TYPE_ICONS: Record<string, string> = {
        STRING: 'mdi-format-text',
        NUMBER: 'mdi-numeric',
        BOOLEAN: 'mdi-toggle-switch-outline',
        DATE: 'mdi-calendar',
        TIME: 'mdi-clock-outline',
        DATETIME: 'mdi-calendar-clock',
        TEXT: 'mdi-text-long',
        RICH_TEXT: 'mdi-text-box-outline',
        ENUM: 'mdi-format-list-bulleted',
        RADIO: 'mdi-radiobox-marked',
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

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadAttributes({ search: '' })
        } catch (error) {
            console.error('Error loading attributes:', error)
        } finally {
            loading.value = false
        }
    }

    const handleEdit = async (item: AttributeItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog.
        editItem.value = null
        await nextTick()
        editItem.value = item
    }

    const handleDelete = async (item: AttributeItem): Promise<void> => {
        try {
            await deleteAttribute(item)
            await loadData()
        } catch (error) {
            console.error('Error deleting attribute:', error)
        }
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(loadData)
</script>
