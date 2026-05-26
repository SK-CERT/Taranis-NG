<template>
    <BaseCard
        :multi-select-active="multiSelectActive"
        :show-selection-checkbox="true"
        :preselected="preselected"
        :card-color="selectedColor"
        :class="{ 'read-item': card.read }"
        @card-click="showDetail"
        @selection-change="selectionChanged"
    >
        <!-- Content Slot -->
        <template #content>
            <!-- Header: Source and Date Info -->
            <div class="text-label-small text-grey mb-2">
                <v-row align="center" no-gutters>
                    <v-col cols="auto">
                        <span v-if="firstNewsItem">
                            {{ t('card_item.source') }}:
                            <strong>
                                {{ firstNewsItem?.news_item_data?.osint_source_name || firstNewsItem?.news_item_data?.source || 'Unknown' }}
                                <span v-if="firstNewsItem?.news_item_data?.osint_source_type">
                                    ({{ firstNewsItem.news_item_data.osint_source_type.split(' ')[0] }})
                                </span>
                            </strong>
                        </span>
                    </v-col>
                    <v-spacer />
                    <v-col cols="auto">
                        <span v-if="firstNewsItem">
                            <strong>{{ t('card_item.published') }}:</strong>
                            {{ firstNewsItem?.news_item_data?.published || 'N/A' }}
                        </span>
                    </v-col>
                    <v-spacer />
                    <v-col cols="auto">
                        <strong>{{ t('card_item.collected') }}:</strong>
                        {{ card.created }}
                    </v-col>
                </v-row>
            </div>

            <!-- Title -->
            <h3 class="mb-2" style="font-size: 1.25rem; font-weight: 700; line-height: 1.35; color: rgba(255, 255, 255, 0.95)">
                {{ card.title }}
            </h3>

            <!-- Description -->
            <p v-if="!hideReviews" class="text-grey mb-3">
                {{ card.description }}
            </p>

            <!-- Footer: Metadata Badges and Actions -->
            <v-row align="center" no-gutters>
                <v-col class="d-flex align-center flex-wrap" style="gap: 12px">
                    <!-- Source Link URL (non-clickable text) -->
                    <span
                        v-if="!hideSourceLinks && firstNewsItem?.news_item_data?.link"
                        class="text-label-small text-primary"
                        style="display: inline-block; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                    >
                        {{ firstNewsItem?.news_item_data?.link }}
                    </span>

                    <!-- Aggregate Badge -->
                    <v-chip v-if="newsItemsCount > 1" size="small" color="primary" variant="outlined">
                        <v-icon start>mdi-file-multiple</v-icon>
                        {{ t('card_item.aggregated_items') }}: {{ newsItemsCount }}
                    </v-chip>

                    <!-- In Reports Badge -->
                    <v-chip
                        v-if="inReportsCount > 0"
                        size="small"
                        color="orange"
                        variant="outlined"
                        :disabled="analyzeSelector"
                        :style="analyzeSelector ? '' : 'cursor: pointer'"
                        @click.stop="!analyzeSelector && showInReports()"
                    >
                        <v-icon start>mdi-file-document</v-icon>
                        {{ t('card_item.in_analyze') }}
                        <span v-if="inReportsCount > 1">&nbsp;({{ inReportsCount }})</span>
                    </v-chip>

                    <!-- Comments Icon -->
                    <v-icon v-if="hasComments" color="orange" size="small">mdi-comment</v-icon>
                </v-col>

                <!-- Actions -->
                <v-col v-if="!multiSelectActive && !analyzeSelector" cols="auto" class="d-flex align-center" style="gap: 4px">
                    <AssessItemActions
                        :item="card"
                        size="small"
                        variant="text"
                        icon-size="default"
                        :show-counts="true"
                        show-create-report
                        @action="handleCardAction"
                    />
                </v-col>
            </v-row>
        </template>
    </BaseCard>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAssessStore } from '@/stores/assess'
    import { useAuth } from '@/composables/useAuth'
    import { deleteNewsItemAggregate } from '@/api/assess'
    import BaseCard from '@/components/common/BaseCard.vue'
    import AssessItemActions from '@/components/assess/AssessItemActions.vue'

    type NewsItemData = {
        osint_source_name?: string
        source?: string
        osint_source_type?: string
        published?: string
        link?: string
        [key: string]: unknown
    }

    type NewsItemEntry = {
        news_item_data?: NewsItemData
        [key: string]: unknown
    }

    type AssessCard = {
        id: number | string
        title?: string
        description?: string
        comments?: string
        created?: string
        read?: boolean
        modify?: boolean
        access?: boolean
        in_reports_count?: number
        news_items?: NewsItemEntry[]
        [key: string]: any
    }

    const props = withDefaults(
        defineProps<{
            card: AssessCard
            data_set?: string
            preselected?: boolean
            analyzeSelector?: boolean
            hideReviews?: boolean
            hideSourceLinks?: boolean
            highlightWordlist?: boolean
        }>(),
        {
            data_set: 'assess',
            preselected: false,
            analyzeSelector: false,
            hideReviews: false,
            hideSourceLinks: false,
            highlightWordlist: false
        }
    )

    const emit = defineEmits<{
        (e: 'show-detail', card: AssessCard): void
        (e: 'update-item', card: AssessCard, action: string): void
        (e: 'delete-item', card: AssessCard): void
        (e: 'show-reports-for-item', card: AssessCard): void
    }>()

    const { t } = useI18n()
    const assessStore = useAssessStore()
    const { checkPermission } = useAuth()

    const firstNewsItem = computed(() => props.card.news_items?.[0])
    const newsItemsCount = computed(() => props.card.news_items?.length ?? 0)
    const inReportsCount = computed(() => props.card.in_reports_count ?? 0)

    const multiSelectActive = computed(() => assessStore.getMultiSelect)

    const selectedColor = computed(() => {
        return assessStore.selectedItems.has(props.card.id) ? 'orange-lighten-4' : ''
    })

    const hasComments = computed(() => {
        if (!props.card.comments) return false
        // Strip HTML tags and check if there's actual content
        const plainText = props.card.comments.replace(/<[^>]*>/g, '').trim()
        return plainText.length > 0
    })

    const selectionChanged = (isSelected: boolean): void => {
        if (isSelected) {
            assessStore.select({ type: 'news_item_aggregate', id: props.card.id, item: props.card })
        } else {
            assessStore.deselect({ type: 'news_item_aggregate', id: props.card.id })
        }
    }

    const showDetail = (): void => {
        emit('show-detail', props.card)
    }

    const showInReports = (): void => {
        emit('show-reports-for-item', props.card)
    }

    const handleCardAction = (action: string): void => {
        if (action === 'delete') {
            handleDelete()
        } else {
            updateCard(action)
        }
    }

    const updateCard = (action: string): void => {
        emit('update-item', props.card, action)
    }

    const handleDelete = async (): Promise<void> => {
        try {
            await deleteNewsItemAggregate('', props.card.id)
            emit('delete-item', props.card)

            // Show success notification
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: 'common.deleted_successfully' }
                })
            )
        } catch (error: unknown) {
            console.error('Error deleting news item aggregate:', error)

            const responseData = (error as { response?: { data?: unknown } } | undefined)?.response?.data
            const isAggregateInUse =
                responseData === 'aggregate_in_use' ||
                (responseData as { error?: string } | undefined)?.error === 'aggregate_in_use' ||
                (typeof responseData === 'string' && responseData.includes('aggregate_in_use'))

            // Check if it's an "in use" error
            if (isAggregateInUse) {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: {
                            type: 'error',
                            message: t('error.aggregate_in_use')
                        }
                    })
                )
            } else {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: {
                            type: 'error',
                            message: t('error.server_error')
                        }
                    })
                )
            }
        }
    }
</script>

<style scoped>
    .read-item {
        opacity: 0.7;
    }

    .read-item:hover {
        opacity: 1;
    }
</style>
