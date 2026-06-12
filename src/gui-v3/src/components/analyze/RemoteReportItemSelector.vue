<template>
    <v-container>
        <!-- Activate Button -->
        <v-btn v-if="canModify && groups.length > 0" variant="elevated" size="small" class="mb-4" @click="openSelector">
            <v-icon start> mdi-plus </v-icon>
            {{ t('report_item.select_remote') }}
        </v-btn>

        <!-- Dialog Container -->
        <v-dialog v-model="selectorOpen" fullscreen persistent>
            <v-card flat>
                <!-- Fixed Toolbar -->
                <v-toolbar color="primary" dark sticky>
                    <v-btn icon @click="handleClose">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{ t('report_item.select_remote') }}</v-toolbar-title>
                    <v-spacer />
                    <v-btn @click="handleAdd">
                        <v-icon start> mdi-plus-box </v-icon>
                        {{ t('common.add') }}
                    </v-btn>
                </v-toolbar>

                <!-- Main Content Row -->
                <v-row no-gutters class="mt-12">
                    <!-- Left Sidebar: Groups -->
                    <v-col
                        cols="auto"
                        class="bg-surface pa-0"
                        style="max-width: 96px; min-height: calc(100vh - 64px); border-right: 1px solid rgba(0, 0, 0, 0.12); overflow-y: auto"
                    >
                        <v-list v-model:selected="selectedGroupList" density="compact" nav>
                            <v-list-item v-for="link in links" :key="link.id" :value="link.id" class="px-1" @click="changeGroup(link.id)">
                                <template #prepend>
                                    <v-icon>{{ link.icon }}</v-icon>
                                </template>
                                <v-list-item-title class="text-caption" style="white-space: break-spaces">
                                    {{ link.title }}
                                </v-list-item-title>
                            </v-list-item>
                        </v-list>
                    </v-col>

                    <!-- Main content: Filter toolbar + ContentDataAnalyze -->
                    <v-col class="flex-grow-1 pa-0">
                        <div class="bg-surface pa-3" style="position: sticky; top: 0; z-index: 100">
                            <ToolbarFilterAnalyze ref="toolbarFilter" :show-group-toolbar="false" @update-filter="updateFilter" />
                        </div>
                        <ContentDataAnalyze
                            ref="contentData"
                            :show-remove-action="false"
                            :remote-reports="true"
                            card-item="CardAnalyze"
                            @show-remote-report-item-detail="showReportItemDetail"
                            @new-data-loaded="handleNewDataLoaded"
                        />
                    </v-col>
                </v-row>
            </v-card>
        </v-dialog>

        <!-- Remote Report Item Dialog -->
        <RemoteReportItem ref="remoteReportItemDialog" />

        <!-- Selected Items Display -->
        <div v-if="!selectorOpen" class="selected-items-container ml-4 pt-2">
            <CardAnalyze
                v-for="item in value"
                :key="item.id"
                :card="item"
                :show-remove-action="true"
                @show-remote-report-item-detail="showReportItemDetail"
                @remove-report-item-from-selector="removeReportItem"
            />
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze.vue'
    import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
    import CardAnalyze from '@/components/analyze/CardAnalyze.vue'
    import RemoteReportItem from '@/components/analyze/RemoteReportItem.vue'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { useAuth } from '@/composables/useAuth'
    import { updateReportItem, getReportItemData } from '@/api/analyze'
    import { PERMISSIONS } from '@/services/auth/permissions'

    type ReportItem = {
        id: number | string
        tag?: string
        [key: string]: any
    }

    type GroupLink = {
        icon: string
        title: string
        id: string
    }

    type UpdatePayload = {
        add?: boolean
        delete?: boolean
        report_item_id?: number
        remote_report_item_id?: number | string
        remote_report_item_ids?: Array<number | string>
        user_id?: number | string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const { checkPermission, getUserId } = useAuth()
    const analyzeStore = useAnalyzeStore()

    const props = withDefaults(
        defineProps<{
            values?: ReportItem[]
            modify?: boolean
            edit?: boolean
            reportItemId?: number | null
        }>(),
        {
            values: () => [],
            modify: false,
            edit: false,
            reportItemId: null
        }
    )

    const emit = defineEmits<{
        (e: 'remote-report-items-changed', payload: null): void
    }>()

    const selectorOpen = ref<boolean>(false)
    const value = ref<ReportItem[]>(props.values || [])
    const groups = ref<string[]>([])
    const links = ref<GroupLink[]>([])
    const selectedGroupId = ref<string | null>(null)
    const selectedGroupList = ref<string[]>([])
    const toolbarFilter = ref<any>(null)
    const contentData = ref<any>(null)
    const remoteReportItemDialog = ref<any>(null)

    const canModify = computed(() => {
        if (!props.edit) return true
        return checkPermission(PERMISSIONS.ANALYZE_UPDATE) && props.modify
    })

    const loadGroups = async (): Promise<void> => {
        try {
            await analyzeStore.loadReportItemGroups({ search: '' })
            const allGroups = analyzeStore.getReportItemGroups
            groups.value = Array.isArray(allGroups) ? allGroups.filter((group): group is string => typeof group === 'string') : []

            links.value = groups.value.map((group: string) => ({
                icon: 'mdi-arrow-down-bold-circle-outline',
                title: group,
                id: group
            }))

            // Set initial group
            if (links.value.length > 0) {
                const currentGroup = analyzeStore.getCurrentReportItemGroup as string | null
                if (currentGroup) {
                    selectedGroupId.value = currentGroup
                } else {
                    selectedGroupId.value = links.value[0]?.id || ''
                    await analyzeStore.changeCurrentReportItemGroup(selectedGroupId.value)
                }
                selectedGroupList.value = [selectedGroupId.value]
            }
        } catch {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.load_groups') }
                })
            )
        }
    }

    const changeGroup = async (groupId: string): Promise<void> => {
        selectedGroupId.value = groupId
        selectedGroupList.value = [groupId]
        await analyzeStore.changeCurrentReportItemGroup(groupId)
        if (contentData.value) {
            contentData.value.updateData(false, false)
        }
    }

    const updateFilter = (filter: Record<string, unknown>): void => {
        if (contentData.value) {
            contentData.value.updateFilter(filter)
        }
    }

    const handleNewDataLoaded = (count: number): void => {
        if (toolbarFilter.value) {
            toolbarFilter.value.updateDataCount(count)
        }
    }

    const showReportItemDetail = (reportItem: ReportItem): void => {
        if (remoteReportItemDialog.value) {
            remoteReportItemDialog.value.showDetail(reportItem)
        }
    }

    const handleAdd = async (): Promise<void> => {
        const rawSelection = analyzeStore.getSelectionReport
        const selection: Array<{ item: ReportItem }> = Array.isArray(rawSelection)
            ? rawSelection
                  .map((entry): { item: ReportItem } | null => {
                      if (!entry || typeof entry !== 'object') return null
                      const candidate = (entry as { item?: unknown }).item
                      if (!candidate || typeof candidate !== 'object') return null
                      const id = (candidate as { id?: unknown }).id
                      if (typeof id !== 'string' && typeof id !== 'number') return null
                      return { item: candidate as ReportItem }
                  })
                  .filter((entry): entry is { item: ReportItem } => entry !== null)
            : []
        const addedValues: ReportItem[] = []
        const data: UpdatePayload = {
            add: true,
            remote_report_item_ids: []
        }

        if (typeof props.reportItemId === 'number') {
            data.report_item_id = props.reportItemId
        }

        selection.forEach((selectedItem: { item: ReportItem }) => {
            const found = value.value.some((item) => item.id === selectedItem.item.id)
            if (!found) {
                addedValues.push(selectedItem.item)
                if (data.remote_report_item_ids) {
                    data.remote_report_item_ids.push(selectedItem.item.id)
                }
            }
        })

        if (props.edit && props.reportItemId && props.reportItemId > 0) {
            try {
                await updateReportItem(props.reportItemId, data)
                value.value.push(...addedValues)
            } catch {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'error', message: t('error.save_failed') }
                    })
                )
                return
            }
        } else {
            value.value.push(...addedValues)
        }

        emit('remote-report-items-changed', null)
        handleClose()
    }

    const removeReportItem = async (reportItem: ReportItem): Promise<void> => {
        const data: UpdatePayload = {
            delete: true,
            remote_report_item_id: reportItem.id
        }

        if (props.edit && props.reportItemId && props.reportItemId > 0) {
            try {
                await updateReportItem(props.reportItemId, data)
                const index = value.value.findIndex((item) => item.id === reportItem.id)
                if (index > -1) {
                    value.value.splice(index, 1)
                }
            } catch {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'error', message: t('error.delete_failed') }
                    })
                )
                return
            }
        } else {
            const index = value.value.findIndex((item) => item.id === reportItem.id)
            if (index > -1) {
                value.value.splice(index, 1)
            }
        }

        emit('remote-report-items-changed', null)
    }

    const openSelector = (): void => {
        analyzeStore.multiSelectReport(true)
        selectorOpen.value = true
        if (contentData.value) {
            contentData.value.updateData(false, false)
        }
    }

    const handleClose = (): void => {
        analyzeStore.multiSelectReport(false)
        selectorOpen.value = false
    }

    const handleReportItemUpdated = async (dataInfo: UpdatePayload): Promise<void> => {
        if (!props.edit || !props.reportItemId || props.reportItemId <= 0 || props.reportItemId !== dataInfo.report_item_id) return
        if (dataInfo.user_id === getUserId()) return

        try {
            if (dataInfo.add !== undefined) {
                const response = await getReportItemData(props.reportItemId, dataInfo)
                if (response?.data?.remote_report_items) {
                    value.value.push(...response.data.remote_report_items)
                }
            } else if (dataInfo.delete !== undefined) {
                const index = value.value.findIndex((item) => item.id === dataInfo.remote_report_item_id)
                if (index > -1) {
                    value.value.splice(index, 1)
                }
            }

            emit('remote-report-items-changed', null)
        } catch {
            // Silent error handling for SSE updates
        }
    }

    const handleReportItemUpdatedEvent = (event: Event): void => {
        const customEvent = event as CustomEvent<UpdatePayload>
        handleReportItemUpdated(customEvent.detail)
    }

    onMounted(async () => {
        await loadGroups()
        window.addEventListener('report-item-updated', handleReportItemUpdatedEvent)
    })

    onUnmounted(() => {
        window.removeEventListener('report-item-updated', handleReportItemUpdatedEvent)
    })

    defineExpose({
        openSelector
    })
</script>

<style scoped>
    .selected-items-container {
        padding: 0;
        margin: 0;
        background: white;
    }
</style>
