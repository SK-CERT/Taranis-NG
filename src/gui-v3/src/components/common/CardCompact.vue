<template>
    <v-container
        fluid
        :class="isDenseList ? 'pa-0' : 'pa-2'"
    >
        <div
            class="card-container d-flex align-center"
            :class="{ 'ga-3': multiSelectActive }"
        >
            <!-- Checkbox for multi-select -->
            <div
                v-if="multiSelectActive"
                class="checkbox-column"
                @click.stop
            >
                <v-checkbox
                    v-model="internalSelected"
                    density="compact"
                    hide-details
                    @update:model-value="emitSelectionChange"
                />
            </div>

            <!-- Card -->
            <v-hover v-slot="{ isHovering, props: hoverProps }">
                <v-card
                    v-bind="hoverProps"
                    :elevation="isDenseList ? 0 : isHovering ? 12 : 2"
                    class="card-compact flex-grow-1"
                    :class="{
                        'card-compact--review review-list__row': isReviewCard,
                        'card-compact--list': listMode
                    }"
                    @click="handleClick"
                >
                    <v-card-text class="compact-card__body">
                        <!-- Top-aligned so every field label sits at the same height: with
                             align="center" a column whose value is empty (or shorter than its
                             neighbours) gets centred on its own, dropping its label lower than
                             the rest. The icon and the delete button stay centred individually. -->
                        <v-row
                            align="start"
                            class="compact-card__row"
                        >
                            <!-- Icon/Tag -->
                            <v-col
                                cols="auto"
                                class="compact-card__icon align-self-center"
                            >
                                <v-icon
                                    :size="isDenseList ? 'small' : 'large'"
                                    color="primary"
                                >
                                    {{ card.tag || ICONS.FILE_DOCUMENT }}
                                </v-icon>
                            </v-col>

                            <!-- Title -->
                            <v-col class="compact-card__primary">
                                <div class="text-label-small text-grey">
                                    {{ typeLabel }}
                                </div>
                                <div class="text-body-large card-field-value">
                                    {{ typeValue }}
                                </div>
                            </v-col>

                            <!-- Description/Subtitle -->
                            <v-col v-if="card.subtitle || card.description || isOsintSource || isModulePreset">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.description') }}
                                </div>
                                <div class="text-body-medium card-field-value">
                                    {{ card.subtitle || card.description || '' }}
                                </div>
                            </v-col>

                            <!-- URL (nodes) -->
                            <v-col v-if="card.api_url">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.url') }}
                                </div>
                                <div class="text-body-medium card-field-value">
                                    {{ card.api_url }}
                                </div>
                            </v-col>

                            <!-- Last Seen (nodes) -->
                            <v-col v-if="card.last_seen">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_seen') }}
                                </div>
                                <div class="text-body-medium card-field-value">
                                    {{ card.last_seen || '' }}
                                </div>
                            </v-col>

                            <!-- Last Attempt / Last Collected (OSINT sources) — last_collected is
                                 empty until a source is collected successfully. -->
                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_attempted') }}
                                </div>
                                <div class="text-body-medium card-field-value">
                                    {{ card.last_attempted || '' }}
                                </div>
                            </v-col>

                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_collected') }}
                                </div>
                                <div class="text-body-medium card-field-value">
                                    {{ card.last_collected || '' }}
                                </div>
                            </v-col>

                            <!-- Last Error (OSINT sources) -->
                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_error') }}
                                </div>
                                <div class="text-body-medium text-error card-field-value">
                                    {{ card.last_error_message || '' }}
                                </div>
                            </v-col>

                            <v-col
                                v-if="isReviewCard"
                                cols="auto"
                                class="compact-review-meta align-self-center"
                            >
                                <v-chip
                                    v-if="hasWorkflowState && card.state"
                                    :color="card.state.color || 'primary'"
                                    variant="tonal"
                                    size="x-small"
                                    :title="card.state.description"
                                >
                                    <v-icon
                                        v-if="card.state.icon"
                                        start
                                        size="13"
                                    >
                                        {{ card.state.icon }}
                                    </v-icon>
                                    {{ stateLabel }}
                                </v-chip>

                                <v-chip
                                    v-if="!hasWorkflowState && inProgressReportsCount > 0"
                                    color="orange"
                                    variant="tonal"
                                    size="x-small"
                                >
                                    <v-icon
                                        start
                                        size="13"
                                        >mdi-progress-clock</v-icon
                                    >
                                    {{ t('card_item.in_analyze') }}
                                    <span v-if="inProgressReportsCount > 1">&nbsp;{{ inProgressReportsCount }}</span>
                                </v-chip>

                                <v-chip
                                    v-if="!hasWorkflowState && completedReportsCount > 0"
                                    color="green"
                                    variant="tonal"
                                    size="x-small"
                                >
                                    <v-icon
                                        start
                                        size="13"
                                        >mdi-check-circle</v-icon
                                    >
                                    {{ t('card_item.analyzed') }}
                                    <span v-if="completedReportsCount > 1">&nbsp;{{ completedReportsCount }}</span>
                                </v-chip>

                                <span
                                    v-if="reviewItemCount > 0"
                                    class="compact-review-count"
                                    :title="reviewCountTitle"
                                >
                                    <v-icon size="14">mdi-newspaper-variant-outline</v-icon>
                                    {{ reviewItemCount }}
                                </span>
                            </v-col>

                            <!-- Actions -->
                            <v-col
                                v-if="canDelete"
                                cols="auto"
                                class="align-self-center"
                            >
                                <ActionButton
                                    action="delete"
                                    :disabled="isProtected"
                                    @click.stop="showDeleteDialog"
                                />
                            </v-col>
                        </v-row>
                    </v-card-text>
                </v-card>
            </v-hover>
        </div>

        <!-- Delete confirmation dialog -->
        <ConfirmationDialog
            v-model="deleteDialog"
            :message="card.title || card.name || ''"
            max-width="400"
            @confirm="handleDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import type { PermissionKey } from '@/types/permissions'
    import { ICONS } from '@/config/ui-constants'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type CardData = {
        id?: string | number
        title?: string
        title_prefix?: string
        name?: string
        subtitle?: string
        description?: string
        tag?: string
        api_url?: string
        last_seen?: string
        collector_id?: string
        collector?: {
            type?: string
            name?: string
        }
        last_attempted?: string
        last_collected?: string
        last_error_message?: string
        default?: boolean
        presenter_id?: string
        presenter_name?: string
        publisher_id?: string
        bot_id?: string
        item_name?: string
        report_type_name?: string
        product_type_name?: string
        report_items_count?: number
        news_items_count?: number
        in_reports_count?: number
        completed_reports_count?: number
        state?: {
            color?: string
            icon?: string
            name?: string
            display_name?: string
            description?: string
        }
        news_items?: Array<{
            news_item_data?: {
                osint_source_name?: string
                source?: string
                osint_source_type?: string
            }
        }>
    }

    const props = withDefaults(
        defineProps<{
            card: CardData
            deletePermission?: string
            multiSelectActive?: boolean
            preselected?: boolean
            lockDefault?: boolean
            listMode?: boolean
        }>(),
        {
            deletePermission: '',
            multiSelectActive: false,
            preselected: false,
            lockDefault: false,
            listMode: false
        }
    )

    const emit = defineEmits(['click', 'delete', 'edit', 'show-detail', 'selection-change'])

    const { t, te } = useI18n()
    const { checkPermission } = useAuth()

    const deleteDialog = ref(false)
    const internalSelected = ref<boolean>(props.preselected)

    // Watch preselected prop and sync with internalSelected
    watch(
        () => props.preselected,
        (newValue: boolean) => {
            internalSelected.value = newValue
        }
    )

    const canDelete = computed(() => {
        if (!props.deletePermission) return false
        return checkPermission(props.deletePermission as PermissionKey)
    })

    // Protected (default) items cannot be deleted — the backend forbids it (e.g. the default
    // "Uncategorized" OSINT source group). The card stays clickable; the dialog opens read-only.
    // Enabled per view via lock-default.
    const isProtected = computed(() => props.lockDefault && props.card?.default === true)

    // OSINT source cards always carry a collector_id; for them we always render the
    // description and collection-status columns (matching the Vue 2 card), with an em-dash
    // fallback when a value is empty.
    const isOsintSource = computed(() => props.card?.collector_id != null)

    // Product type, publisher preset and bot preset cards each carry the id of the module they
    // drive. Like OSINT sources they always render the description column: descriptions are
    // optional on these records, and an empty one would otherwise drop the whole labelled column
    // and leave the card looking unlike its siblings.
    const isModulePreset = computed(() => props.card?.presenter_id != null || props.card?.publisher_id != null || props.card?.bot_id != null)

    const isReviewCard = computed(
        () => props.card?.report_type_name != null || props.card?.product_type_name != null || Array.isArray(props.card?.news_items)
    )
    const isDenseList = computed(() => isReviewCard.value || props.listMode)
    const hasWorkflowState = computed(() => props.card?.report_type_name != null || props.card?.product_type_name != null)
    const reviewItemCount = computed(() =>
        Number(props.card?.report_items_count ?? props.card?.news_items_count ?? props.card?.news_items?.length ?? 0)
    )
    const reviewCountTitle = computed(() =>
        props.card?.product_type_name != null ? t('nav_menu.report_items') : t('card_item.aggregated_items')
    )
    const completedReportsCount = computed(() => Number(props.card?.completed_reports_count ?? 0))
    const inProgressReportsCount = computed(() =>
        Math.max(0, Number(props.card?.in_reports_count ?? 0) - completedReportsCount.value)
    )
    const stateLabel = computed(() => {
        const label = props.card?.state?.display_name || props.card?.state?.name || ''
        const key = `workflow.states.${label}`
        return label && te(key) ? t(key) : label
    })

    const typeLabel = computed(() => {
        // Node-type items (collectors/presenters/publishers/bots nodes) carry an api_url.
        if (props.card?.api_url) {
            return t('card_item.node')
        }
        // OSINT source cards label the name column with the source's collector (e.g. "RSS Collector")
        // rather than the generic "Title", so the collection method is visible without opening the card.
        if (isOsintSource.value) {
            return props.card.collector?.name || props.card.collector?.type || t('card_item.title')
        }
        // Same for the module behind a product type (presenter_name) and behind a publisher or
        // bot preset (item_name) — the backend presentation schemas expose the module name only.
        if (props.card?.presenter_name) {
            return props.card.presenter_name
        }
        if (props.card?.item_name) {
            return props.card.item_name
        }
        if (props.card?.report_type_name) {
            return props.card.report_type_name
        }
        if (props.card?.product_type_name) {
            return props.card.product_type_name
        }
        const sourceName =
            props.card?.news_items?.[0]?.news_item_data?.osint_source_name || props.card?.news_items?.[0]?.news_item_data?.source
        const sourceType = props.card?.news_items?.[0]?.news_item_data?.osint_source_type
        if (sourceName) {
            return sourceType ? `${sourceName} (${sourceType})` : sourceName
        }
        return t('card_item.title')
    })

    const typeValue = computed(() => {
        const value = props.card?.title || props.card?.name || ''
        return props.card?.title_prefix ? `${props.card.title_prefix} — ${value}` : value
    })

    const handleClick = (): void => {
        emit(isReviewCard.value ? 'show-detail' : 'edit', props.card as CardData)
    }

    const showDeleteDialog = (): void => {
        deleteDialog.value = true
    }

    const handleDelete = (): void => {
        deleteDialog.value = false
        emit('delete', props.card as CardData)
    }

    const emitSelectionChange = (): void => {
        emit('selection-change', internalSelected.value)
    }
</script>

<style scoped>
    /* Reserve one line even when the value is empty, so a card with no description is the
       same height as one with a description and the rows in the list stay even. */
    .card-field-value {
        min-height: 1.25em;
        min-height: 1lh;
    }

    .card-container {
        width: 100%;
        display: flex;
        flex-direction: row;
        align-items: center;
        flex: 1 1 0;
    }

    .checkbox-column {
        flex-shrink: 0;
        display: flex;
        align-items: flex-start;
        padding-top: 12px;
    }

    .card-compact {
        cursor: pointer;
        transition: all 0.3s ease;
        flex-grow: 1;
    }

    .card-compact:hover {
        transform: translateY(-2px);
    }

    .card-compact--review,
    .card-compact--list {
        border: 1px solid var(--review-list-border);
        border-inline-width: 0;
        border-radius: 0;
        background: var(--review-list-row);
        box-shadow: none;
        transform: none !important;
        transition:
            border-color 0.15s ease,
            background-color 0.15s ease;
    }

    .card-compact--review:hover,
    .card-compact--list:hover {
        background: var(--review-list-row-hover);
    }

    .card-compact--review .compact-card__body,
    .card-compact--list .compact-card__body {
        padding: 0.35rem 0.55rem !important;
    }

    .card-compact--review .compact-card__row,
    .card-compact--list .compact-card__row {
        margin: 0;
        align-items: center !important;
    }

    .card-compact--review .compact-card__row > :deep(.v-col),
    .card-compact--list .compact-card__row > :deep(.v-col) {
        min-width: 0;
        padding: 0.15rem 0.35rem;
    }

    .card-compact--review .compact-card__icon,
    .card-compact--list .compact-card__icon {
        padding-inline: 0.25rem 0.45rem !important;
    }

    .card-compact--review .card-field-value,
    .card-compact--list .card-field-value {
        overflow: hidden;
        min-height: 1.2em;
        font-size: 0.84rem;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .card-compact--review .compact-card__primary .card-field-value,
    .card-compact--list .compact-card__primary .card-field-value {
        color: rgb(var(--v-theme-on-surface));
        font-weight: 650;
    }

    .card-compact--review :deep(.text-label-small),
    .card-compact--list :deep(.text-label-small) {
        font-size: 0.64rem;
        line-height: 1.1;
    }

    .compact-review-meta {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        width: 12rem;
        max-width: 12rem;
        flex: 0 0 12rem;
        gap: 0.3rem;
        white-space: nowrap;
    }

    .compact-review-meta :deep(.v-chip) {
        height: 22px;
        border-radius: 3px;
        font-size: 0.68rem;
        font-weight: 650;
    }

    .compact-review-count {
        display: inline-flex;
        align-items: center;
        gap: 0.2rem;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.72rem;
        font-weight: 650;
    }

    .card-compact--review + * {
        margin-top: 0;
    }
</style>
