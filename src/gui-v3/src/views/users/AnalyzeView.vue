<template>
    <ViewLayout integrated-toolbar>
        <template #panel>
            <ToolbarFilterAnalyze
                ref="toolbarFilter"
                :multi-select="!isRemoteScope"
                title="nav_menu.report_items"
                total-count-title="toolbar_filter.total_count"
                :show-add-button="canCreateReportItem"
                @update-filter="updateFilter"
                @update-data="updateData"
                @add-new="handleAddNew"
            />
        </template>
        <template #content>
            <ContentDataAnalyze
                ref="contentData"
                :show-remove-action="false"
                :remote-reports="false"
                :selection="analyzeStore.getSelectionReport"
                :disable-actions="isRemoteScope"
                @new-data-loaded="newDataLoaded"
                @update-showing-count="updateShowingCount"
                @show-report-item-detail="showReportItemDetail"
                @show-remote-report-item-detail="showRemoteReportItemDetail"
            />
        </template>
    </ViewLayout>

    <NewReportItem
        ref="newReportItemRef"
        :show-button="false"
        @data-updated="updateData"
    />
    <RemoteReportItem ref="remoteReportItemRef" />
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useRoute, onBeforeRouteLeave } from 'vue-router'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { useAuth } from '@/composables/useAuth'
    import ViewLayout from '@/components/layouts/ViewLayout.vue'
    import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
    import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import RemoteReportItem from '@/components/analyze/RemoteReportItem.vue'
    import { isRemoteAnalyzeRoute } from '@/utils/analyze-routing'

    const route = useRoute()
    const analyzeStore = useAnalyzeStore()
    const { checkPermission } = useAuth()
    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)
    const newReportItemRef = ref<any>(null)
    const remoteReportItemRef = ref<any>(null)

    const isRemoteScope = computed(() => isRemoteAnalyzeRoute(route))

    watch(
        isRemoteScope,
        (remote) => {
            if (remote) analyzeStore.multiSelectReport(false)
        },
        { immediate: true }
    )

    const canCreateReportItem = computed(() => {
        return checkPermission('ANALYZE_CREATE') && !isRemoteScope.value
    })

    const handleAddNew = (): void => {
        if (newReportItemRef.value) {
            newReportItemRef.value.openDialog()
        }
    }

    const newDataLoaded = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateDataCount(count)
        }
    }

    const updateShowingCount = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateShowingCount(count)
        }
    }

    const updateFilter = (filter: Record<string, unknown>): void => {
        if (contentData.value) {
            contentData.value.updateFilter(filter)
        }
    }

    const updateData = (): void => {
        if (contentData.value) {
            contentData.value.updateData(false, true)
        }
    }

    const showReportItemDetail = (reportItem: unknown): void => {
        if (newReportItemRef.value) {
            newReportItemRef.value.showDetail(reportItem)
        }
    }

    const showRemoteReportItemDetail = (reportItem: unknown): void => {
        remoteReportItemRef.value?.showDetail(reportItem)
    }

    onBeforeRouteLeave(() => {
        analyzeStore.multiSelectReport(false)
    })
</script>
