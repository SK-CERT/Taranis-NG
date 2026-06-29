<template>
    <div>
        <BaseCard
            :multi-select-active="multiSelectActive"
            :show-selection-checkbox="true"
            :preselected="preselected"
            :card-class="'card-item'"
            :card-color="selectedColor"
            @card-click="cardItemClick"
            @selection-change="selectionChanged"
        >
            <!-- Content Slot -->
            <template #content>
                <v-row class="align-center">
                    <v-col cols="auto">
                        <v-icon
                            style="font-size: 32px"
                            :icon="card.tag || ICONS.FILE_DOCUMENT"
                            class="ms-2"
                        />
                    </v-col>
                    <v-col>
                        <v-row>
                            <!-- Type Name -->
                            <v-col class="d-flex align-center text-label-medium text-grey">
                                {{ card.report_type_name }}
                            </v-col>
                            <!-- Updated Info, pushed to the right -->
                            <v-col
                                cols="auto"
                                class="d-flex align-center text-label-medium text-grey"
                            >
                                {{ t('card_item.updated') }}:
                                {{ card.last_updated }}
                                <span
                                    v-if="card.updated_by"
                                    class="ms-2"
                                    >{{ card.updated_by }}</span
                                >
                            </v-col>
                        </v-row>
                        <!-- Title Row + State (below Updated) -->
                        <v-row
                            class="mt-2"
                            align="center"
                        >
                            <v-col>
                                <div class="text-title-medium">
                                    <span v-if="card.title_prefix">{{ card.title_prefix }} -</span>
                                    {{ card.title }}
                                    <span
                                        v-if="card.news_items_count"
                                        class="text-grey ms-1"
                                        >({{ card.news_items_count }})</span
                                    >
                                </div>
                            </v-col>
                            <v-col
                                v-if="card.state"
                                cols="auto"
                                class="d-flex justify-end align-center"
                                :title="card.state.description"
                            >
                                <v-icon :color="card.state.color">
                                    {{ card.state.icon }}
                                </v-icon>
                                <span class="text-body-large ms-2">
                                    {{
                                        $te('workflow.states.' + card.state.display_name)
                                            ? $t('workflow.states.' + card.state.display_name)
                                            : card.state.display_name
                                    }}
                                </span>
                            </v-col>
                        </v-row>
                    </v-col>
                    <!-- Actions -->
                    <v-col
                        v-if="!disableActions"
                        cols="auto"
                        class="d-flex justify-end"
                    >
                        <!-- Publish -->
                        <ActionButton
                            v-if="canCreateProduct && !showRemoveAction"
                            action="publish"
                            :title="t('analyze.tooltip.publish_item')"
                            @click.stop="handlePublish"
                        />
                        <!-- Delete -->
                        <ActionButton
                            v-if="canDelete && !showRemoveAction"
                            action="delete"
                            :title="t('analyze.tooltip.delete_item')"
                            @click.stop="showDeleteDialog = true"
                        />
                        <!-- Remove from Group -->
                        <ActionButton
                            v-if="canModify && showRemoveAction"
                            action="remove"
                            :title="t('analyze.tooltip.remove_item')"
                            @click.stop="showRemoveDialog = true"
                        />
                    </v-col>
                </v-row>
            </template>
        </BaseCard>

        <!-- Delete Confirmation Dialog -->
        <ConfirmationDialog
            v-model="showDeleteDialog"
            :message="card.title || ''"
            max-width="500px"
            @confirm="handleDelete"
        />

        <!-- Remove Confirmation Dialog -->
        <ConfirmationDialog
            v-model="showRemoveDialog"
            :message="card.title || ''"
            title-key="common.messagebox.remove"
            confirm-label-key="common.remove"
            max-width="500px"
            @confirm="handleRemove"
        />
    </div>
</template>

<script setup lang="ts">
    import { ref, computed } from 'vue'
    import { ICONS } from '@/config/ui-constants'
    import { useI18n } from 'vue-i18n'
    import { useRoute, useRouter } from 'vue-router'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { usePublishStore } from '@/stores/publish'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { deleteReportItem } from '@/api/analyze'
    import BaseCard from '@/components/common/BaseCard.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type AnalyzeCard = {
        id: number | string
        title?: string
        title_prefix?: string
        report_type_name?: string
        tag?: string
        news_items_count?: number
        last_updated?: string
        updated_by?: string
        modify?: boolean
        access?: boolean
        remote_user?: unknown
        state?: {
            name?: string
            color?: string
            icon?: string
            display_name?: string
            description?: string
        } | null
        [key: string]: any
    }

    const props = withDefaults(
        defineProps<{
            card: AnalyzeCard
            showRemoveAction?: boolean
            disableActions?: boolean
            preselected?: boolean
        }>(),
        {
            showRemoveAction: false,
            disableActions: false,
            preselected: false
        }
    )

    const emit = defineEmits<{
        (e: 'remove-report-item-from-selector', card: AnalyzeCard): void
        (e: 'delete-item', card: AnalyzeCard): void
        (e: 'show-detail', card: AnalyzeCard): void
    }>()

    const { t } = useI18n()
    const route = useRoute()
    const router = useRouter()
    const analyzeStore = useAnalyzeStore()
    const publishStore = usePublishStore()
    const { checkPermission } = useAuth()

    const showDeleteDialog = ref<boolean>(false)
    const showRemoveDialog = ref<boolean>(false)

    const canModify = computed(() => {
        return checkPermission(PERMISSIONS.ANALYZE_UPDATE) && (props.card.modify === true || props.card.remote_user !== null)
    })

    const canDelete = computed(() => {
        return checkPermission(PERMISSIONS.ANALYZE_DELETE) && (props.card.modify === true || props.card.remote_user !== null)
    })

    const canCreateProduct = computed(() => {
        return checkPermission(PERMISSIONS.PUBLISH_CREATE) && !route.path.includes('/group/')
    })

    const multiSelectActive = computed(() => {
        return analyzeStore.getMultiSelectReport
    })

    const selectedColor = computed(() => {
        return analyzeStore.selectedReports.has(props.card.id) ? 'orange-lighten-4' : ''
    })

    const itemStatus = computed(() => {
        if (props.card.state) {
            return props.card.state.name
        }
        return 'no_state'
    })

    const selectionChanged = (isSelected: boolean): void => {
        if (isSelected) {
            analyzeStore.selectReport({ id: props.card.id, item: props.card })
        } else {
            analyzeStore.deselectReport({ id: props.card.id, item: props.card })
        }
    }

    const cardItemClick = (_event?: unknown): void => {
        if (checkPermission(PERMISSIONS.ANALYZE_ACCESS) && (props.card.access === true || props.card.remote_user !== null)) {
            // Emit event to open report item detail dialog
            emit('show-detail', props.card)
        }
    }

    const handleDelete = async (): Promise<void> => {
        showDeleteDialog.value = false
        try {
            await deleteReportItem(props.card)

            // Emit event to parent to remove from list and trigger animation
            emit('delete-item', props.card)

            // Show success notification
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: 'common.deleted_successfully' }
                })
            )
        } catch (error: unknown) {
            console.error('Error deleting report item:', error)
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.server_error') }
                })
            )
        }
    }

    const handleRemove = (): void => {
        showRemoveDialog.value = false
        emit('remove-report-item-from-selector', props.card)
    }

    const handlePublish = (): void => {
        publishStore.pendingNewProduct = [props.card]
        router.push('/publish')
    }
</script>

<style scoped>
    .card-item {
        cursor: pointer;
        transition: all 0.3s ease;
    }
</style>
