<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.reportItemTypesConfig.total_count"
            total-count-title="reports.types.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewReportType
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.reportItemTypesConfig.items"
            card-item="CardCompact"
            delete-permission="CONFIG_REPORT_TYPE_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteReportItemType } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewReportType from '@/components/config/reports/NewReportType.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type ReportTypeItem = {
        id?: string | number | null
        title?: string
        description?: string
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<ReportTypeItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadReportItemTypesConfig(filter.value)
        } catch (error) {
            console.error('Error loading report types:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (reportType: ReportTypeItem): Promise<void> => {
        try {
            await deleteReportItemType(reportType)
            console.log('Report type deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting report type:', error)
        }
    }

    const handleEdit = async (reportType: ReportTypeItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog.
        editItem.value = null
        await nextTick()
        editItem.value = reportType
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
