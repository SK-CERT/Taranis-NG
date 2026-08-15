<template>
    <BaseCard
        :multi-select-active="false"
        :show-selection-checkbox="false"
        card-class="aggregate-child-card"
        @card-click="showDetail"
    >
        <template #content>
            <div class="text-label-small text-grey mb-2">
                <v-row align="center">
                    <v-col cols="auto">
                        <i18n-t
                            v-if="sourceType"
                            scope="global"
                            keypath="card_item.source_with_type"
                        >
                            <template #source>
                                <bdi dir="auto">{{ sourceName }}</bdi>
                            </template>
                            <template #type>
                                <bdi dir="auto">{{ sourceType }}</bdi>
                            </template>
                        </i18n-t>
                        <bdi
                            v-else
                            dir="auto"
                            >{{ sourceName }}</bdi
                        >
                    </v-col>
                    <v-spacer />
                    <v-col cols="auto">
                        <i18n-t
                            scope="global"
                            keypath="card_item.published_at"
                        >
                            <template #date>
                                <bdi dir="auto">{{ publishedLabel }}</bdi>
                            </template>
                        </i18n-t>
                    </v-col>
                    <v-spacer />
                    <v-col cols="auto">
                        <i18n-t
                            scope="global"
                            keypath="card_item.collected_at"
                        >
                            <template #date>
                                <bdi dir="auto">{{ collectedLabel }}</bdi>
                            </template>
                        </i18n-t>
                    </v-col>
                </v-row>
            </div>

            <h4 class="mb-2 child-title">
                <bdi dir="auto">
                    <HighlightedText
                        :text="itemTitle"
                        :words="highlightWords"
                        :enabled="highlightWordlist"
                    />
                </bdi>
            </h4>

            <p
                v-if="!hideReviews && itemReview"
                class="text-grey mb-3"
            >
                <bdi dir="auto">
                    <HighlightedText
                        :text="itemReview"
                        :words="highlightWords"
                        :enabled="highlightWordlist"
                    />
                </bdi>
            </p>

            <v-row align="center">
                <v-col
                    class="d-flex align-center flex-wrap"
                    style="gap: 12px"
                >
                    <span
                        v-if="!hideSourceLinks && itemLink"
                        class="text-label-small text-primary source-link"
                    >
                        <bdi dir="ltr">{{ itemLink }}</bdi>
                    </span>
                </v-col>

                <v-col
                    v-if="!analyzeSelector"
                    cols="auto"
                    class="d-flex align-center"
                    style="gap: 4px"
                >
                    <AssessItemActions
                        :item="displayItem"
                        size="small"
                        variant="text"
                        icon-size="default"
                        :show-counts="true"
                        @action="handleAction"
                    />
                </v-col>
            </v-row>
        </template>
    </BaseCard>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import BaseCard from '@/components/common/BaseCard.vue'
    import AssessItemActions from '@/components/assess/AssessItemActions.vue'
    import HighlightedText from '@/components/common/HighlightedText.vue'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { Action, type ActionKey } from '@/types/actions'

    type NewsItemData = {
        osint_source_name?: string
        source?: string
        osint_source_type?: string
        published?: string
        collected?: string
        title?: string
        review?: string
        link?: string
        [key: string]: unknown
    }

    type AssessNewsItem = {
        id: number | string
        title?: string
        description?: string
        comments?: string
        created?: string
        read?: boolean
        important?: boolean
        likes?: number
        dislikes?: number
        me_like?: boolean
        me_dislike?: boolean
        modify?: boolean
        news_item_data?: NewsItemData
        [key: string]: unknown
    }

    type DetailNewsItem = {
        id: number | string
        entityType: 'news_item'
        title: string
        description: string
        comments: string
        created: string
        read: boolean
        important: boolean
        likes: number
        dislikes: number
        me_like: boolean
        me_dislike: boolean
        link: string
        news_items: AssessNewsItem[]
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            newsItem: AssessNewsItem
            analyzeSelector?: boolean
            hideReviews?: boolean
            hideSourceLinks?: boolean
            highlightWordlist?: boolean
            highlightWords?: string[]
        }>(),
        {
            analyzeSelector: false,
            hideReviews: false,
            hideSourceLinks: false,
            highlightWordlist: false,
            highlightWords: () => []
        }
    )

    const emit = defineEmits<{
        (e: 'show-detail', item: DetailNewsItem): void
        (e: 'update-item', item: DetailNewsItem, action: ActionKey): void
        (e: 'delete-item', item: DetailNewsItem): void
    }>()

    const { t } = useI18n()
    const { formatDateTime } = useLocaleFormatters()
    const itemData = computed(() => props.newsItem.news_item_data || {})

    const sourceName = computed(() => itemData.value.osint_source_name || itemData.value.source || t('card_item.unknown_source'))
    const sourceType = computed(() => itemData.value.osint_source_type?.split(' ')[0] || '')
    const publishedDate = computed(() => itemData.value.published || '')
    const formatDisplayDate = (value: string): string => (value ? formatDateTime(value) || value : t('card_item.not_available'))
    const publishedLabel = computed(() => formatDisplayDate(publishedDate.value))
    const collectedDate = computed(() => itemData.value.collected || props.newsItem.created || '')
    const collectedLabel = computed(() => formatDisplayDate(collectedDate.value))
    const itemTitle = computed(() => itemData.value.title || props.newsItem.title || '')
    const itemReview = computed(() => itemData.value.review || props.newsItem.description || '')
    const itemLink = computed(() => itemData.value.link || '')

    const displayItem = computed<DetailNewsItem>(() => ({
        ...props.newsItem,
        entityType: 'news_item',
        title: itemTitle.value,
        description: itemReview.value,
        comments: props.newsItem.comments || '',
        created: collectedDate.value || 'N/A',
        read: Boolean(props.newsItem.read),
        important: Boolean(props.newsItem.important),
        likes: Number(props.newsItem.likes || 0),
        dislikes: Number(props.newsItem.dislikes || 0),
        me_like: Boolean(props.newsItem.me_like),
        me_dislike: Boolean(props.newsItem.me_dislike),
        link: itemLink.value,
        news_items: [props.newsItem]
    }))

    const showDetail = (): void => {
        emit('show-detail', displayItem.value)
    }

    const handleAction = (action: ActionKey): void => {
        if (action === Action.DELETE) {
            emit('delete-item', displayItem.value)
            return
        }

        emit('update-item', displayItem.value, action)
    }
</script>

<style scoped>
    :deep(.aggregate-child-card) {
        margin-inline-start: 32px;
        border-inline-start: 3px solid rgb(var(--v-theme-primary));
    }

    .child-title {
        font-size: 1.05rem;
        line-height: 1.35;
    }

    .source-link {
        display: inline-block;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
