<template>
    <ViewLayout integrated-toolbar>
        <template #panel>
            <ToolbarFilterAssess
                ref="toolbarFilter"
                title="nav_menu.newsitems"
                total_count_title="toolbar_filter.total_count"
                selected_count_title="toolbar_filter.selected_count"
                @update-filter="updateFilter"
                @update-data="updateData"
            >
                <!-- Add News Item: the button is the dialog's activator so the open
                     animation originates from it (matches the Configuration dialogs). -->
                <template #addbutton>
                    <AddNewsItemDialog
                        v-if="canCreateNewsItem"
                        v-model="showAddNewsItemDialog"
                        :manual-sources="assessStore.getManualOSINTSourcesList"
                        :initial-source-id="requestedManualSourceId"
                        @news-item-added="handleNewsItemAdded"
                    >
                        <template #activator="{ props: activatorProps }">
                            <AddNewButton
                                :show="hasManualSources"
                                v-bind="activatorProps"
                            />
                        </template>
                    </AddNewsItemDialog>
                </template>
            </ToolbarFilterAssess>
        </template>

        <template #content>
            <ContentDataAssess
                v-if="canAccessAssess"
                ref="contentData"
                :analyze_selector="analyze_selector"
                :selection="assessStore.getSelection"
                @new-data-loaded="newDataLoaded"
                @card-items-reindex="handleCardItemsReindex"
                @update-showing-count="updateShowingCount"
            />
        </template>
    </ViewLayout>

    <!-- New Report Item Dialog -->
    <NewReportItem ref="newReportItem" />
</template>

<script setup lang="ts">
    import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
    import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { useAssessStore } from '@/stores/assess'
    import ViewLayout from '@/components/layouts/ViewLayout.vue'
    import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'
    import ContentDataAssess from '@/components/assess/ContentDataAssess.vue'
    import AddNewsItemDialog from '@/components/assess/AddNewsItemDialog.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import NewReportItem from '@/components/analyze/NewReportItem.vue'
    import useKeyboard from '@/composables/useKeyboard'
    import { useAuth } from '@/composables/useAuth'
    import Permissions from '@/services/permissions'

    const props = withDefaults(
        defineProps<{
            analyze_selector?: boolean
        }>(),
        {
            analyze_selector: false
        }
    )

    const route = useRoute()
    const router = useRouter()
    const assessStore = useAssessStore()
    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)
    const showAddNewsItemDialog = ref(false)
    const requestedManualSourceId = ref<string | null>(null)
    const newReportItem = ref<any>(null)
    const canCreateNewsItem = computed(() => checkPermission(Permissions.ASSESS_CREATE))
    const canAccessAssess = computed(() => checkPermission(Permissions.ASSESS_ACCESS))
    const hasManualSources = computed(() => assessStore.getManualOSINTSourcesList && assessStore.getManualOSINTSourcesList.length > 0)

    const newDataLoaded = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateDataCount(count)
        }
    }

    const updateFilter = (filter: Record<string, unknown>): void => {
        if (contentData.value) {
            contentData.value.updateFilter(filter)
            assessStore.setFilter(filter)
        }
    }

    const updateData = (reloadAll: boolean = true): void => {
        if (contentData.value) {
            contentData.value.updateData(false, reloadAll)
        }
    }

    const keyboard = useKeyboard('assess', router)

    /**
     * Handle card items reindex event from ContentDataAssess
     * This is emitted when cards are reindexed/updated
     */
    const handleCardItemsReindex = async (mode: string): Promise<void> => {
        // Wait for Vue to update the DOM
        await nextTick()
        keyboard.reindexCardItems(mode)
    }

    // Handle keyboard events for card navigation
    const handleKeyDown = (event: KeyboardEvent): void => {
        keyboard.keyAction(event)
    }

    const updateShowingCount = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateCurrentlyShowingCount(count)
        }
    }

    const handleNewsItemAdded = (): void => {
        // Refresh the data when a new news item is added
        updateData()
    }

    const handleNewReport = (event: CustomEvent): void => {
        if (newReportItem.value) {
            newReportItem.value.openDialog(event.detail)
        }
    }

    // Handle route changes
    const handleRouteChange = (): void => {
        if (contentData.value) {
            contentData.value.updateData(false, false)
        }
    }

    onMounted(async () => {
        const manualSourceQuery = route.query['manualSource']
        const sourceId = Array.isArray(manualSourceQuery) ? manualSourceQuery[0] : manualSourceQuery
        requestedManualSourceId.value = sourceId ?? null
        const manualEntryRequested = route.query['manualEntry'] === 'true'

        // Keep the handoff marker in the URL for create-only users: without it a refresh would
        // correctly fail the ASSESS_ACCESS route guard. Full Assess users get the canonical URL.
        if ((manualSourceQuery !== undefined || manualEntryRequested) && (canAccessAssess.value || !canCreateNewsItem.value)) {
            const query = { ...route.query }
            delete query['manualSource']
            delete query['manualEntry']
            await router.replace({ name: 'assess', params: { groupId: route.params['groupId'] }, query })
        }

        if (canCreateNewsItem.value) {
            // Load manual OSINT sources to show "Add New" button (non-blocking)
            try {
                await assessStore.loadManualOSINTSources()
                if (
                    manualEntryRequested ||
                    (requestedManualSourceId.value &&
                        assessStore.getManualOSINTSourcesList.some(
                            (source) =>
                                typeof source === 'object' &&
                                source !== null &&
                                'id' in source &&
                                String(source.id) === requestedManualSourceId.value
                        ))
                ) {
                    showAddNewsItemDialog.value = true
                }
            } catch (error) {
                console.error('Error loading manual OSINT sources:', error)
            }
        }

        if (route.path.includes('/group/')) {
            handleRouteChange()
        }

        window.addEventListener('new-report', handleNewReport as EventListener)

        // Keyboard initialization
        window.addEventListener('keydown', handleKeyDown)
        keyboard.onInit()
        keyboard.setDetailDialogCloseCallback(() => {
            if (contentData.value?.closeDetailDialog) {
                contentData.value.closeDetailDialog()
            }
        })
        keyboard.setReloadCallback(() => {
            updateData(false)
        })
    })

    // Every group tab is the same route record, so switching between them keeps this view mounted
    // and a selection made in one group would survive into the next. A group action always targets
    // the group in the URL, so acting on that selection would merge news items across groups -
    // which is exactly what hiding the group actions on the "all sources" tab prevents.
    onBeforeRouteUpdate((to, from) => {
        if (to.params['groupId'] !== from.params['groupId']) {
            assessStore.clearSelection()
        }
    })

    onBeforeRouteLeave(() => {
        assessStore.multiSelect(false)
    })

    onUnmounted(() => {
        window.removeEventListener('keydown', handleKeyDown)
        window.removeEventListener('new-report', handleNewReport as EventListener)
    })
</script>
