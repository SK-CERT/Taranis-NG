<template>
    <div>
        <BaseCard
            :multi-select-active="multiSelectActive"
            :show-selection-checkbox="true"
            :preselected="preselected"
            card-class="review-list__row"
            :card-color="selectedColor"
            :card-id="card.id"
            @card-click="cardItemClick"
            @selection-change="selectionChanged"
        >
            <!-- Content Slot -->
            <template #content>
                <article class="report-card">
                    <div class="report-card__icon">
                        <v-icon
                            :icon="card.tag || ICONS.FILE_DOCUMENT"
                            size="22"
                        />
                    </div>

                    <div class="report-card__content">
                        <div class="report-card__meta-row">
                            <span class="report-card__type">{{ card.report_type_name }}</span>
                            <span class="report-card__updated">
                                <v-icon size="14">mdi-clock-outline</v-icon>
                                {{ t('card_item.updated') }} {{ card.last_updated }}
                                <span v-if="card.updated_by">· {{ card.updated_by }}</span>
                            </span>
                        </div>

                        <h2 class="report-card__title">
                            <span
                                v-if="card.title_prefix"
                                class="report-card__prefix"
                                >{{ card.title_prefix }} —</span
                            >
                            {{ card.title }}
                        </h2>

                        <div class="report-card__details">
                            <v-chip
                                v-if="card.state"
                                :color="card.state.color"
                                variant="tonal"
                                size="small"
                                :title="card.state.description"
                                class="report-card__state"
                            >
                                <v-icon
                                    start
                                    size="16"
                                    >{{ card.state.icon }}</v-icon
                                >
                                {{
                                    $te('workflow.states.' + card.state.display_name)
                                        ? $t('workflow.states.' + card.state.display_name)
                                        : card.state.display_name
                                }}
                            </v-chip>

                            <span
                                v-if="card.news_items_count"
                                class="report-card__source-count"
                            >
                                <v-icon size="15">mdi-newspaper-variant-outline</v-icon>
                                {{ card.news_items_count }}
                            </span>
                        </div>
                    </div>

                    <div
                        v-if="!disableActions"
                        class="report-card__actions"
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
                    </div>
                </article>
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
    .report-card {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        gap: 0.65rem;
        min-width: 0;
    }

    .report-card__icon {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        flex: 0 0 auto;
        border-radius: 4px;
        color: rgb(var(--v-theme-primary));
        background: linear-gradient(145deg, rgba(var(--v-theme-primary), 0.16), rgba(var(--v-theme-primary), 0.06));
        box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.12);
    }

    .report-card__content {
        min-width: 0;
    }

    .report-card__meta-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        min-width: 0;
    }

    .report-card__type {
        overflow: hidden;
        color: rgb(var(--v-theme-primary));
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .report-card__updated {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        flex: 0 1 auto;
        color: rgba(var(--v-theme-on-surface), 0.55);
        font-size: 0.72rem;
        white-space: nowrap;
    }

    .report-card__title {
        margin: 0.15rem 0 0.3rem;
        color: rgb(var(--v-theme-on-surface));
        font-size: clamp(0.95rem, 1.2vw, 1.05rem);
        font-weight: 650;
        letter-spacing: -0.012em;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .report-card__prefix {
        color: rgba(var(--v-theme-on-surface), 0.72);
        font-weight: 500;
    }

    .report-card__details {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        min-height: 22px;
    }

    .report-card__state {
        font-weight: 650;
    }

    .report-card__source-count {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        color: rgba(var(--v-theme-on-surface), 0.58);
        font-size: 0.76rem;
    }

    .report-card__actions {
        display: flex;
        align-items: center;
        gap: 0.15rem;
        padding-inline-start: 0.5rem;
        border-inline-start: 1px solid rgba(var(--v-theme-outline), 0.24);
    }

    .report-card__actions :deep(.v-btn) {
        border-radius: 3px;
    }

    @media (max-width: 760px) {
        .report-card {
            grid-template-columns: auto minmax(0, 1fr);
            align-items: start;
        }

        .report-card__meta-row {
            align-items: flex-start;
            flex-direction: column;
            gap: 0.25rem;
        }

        .report-card__updated {
            white-space: normal;
        }

        .report-card__actions {
            grid-column: 2;
            justify-content: flex-end;
            padding-block-start: 0.35rem;
            padding-inline-start: 0;
            border-inline-start: 0;
            border-top: 1px solid rgba(var(--v-theme-outline), 0.2);
        }
    }

    @media (max-width: 480px) {
        .report-card__icon {
            width: 36px;
            height: 36px;
        }
    }
</style>
