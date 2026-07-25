<template>
    <!-- contained renders the dialog inside its positioned ancestor (e.g. the side-by-side
         right column) instead of as a centered, full-screen-overlay modal. -->
    <!-- No `scrollable`: it makes Vuetify force `max-height: 100%` on the card (which
         resolves against an auto-height overlay = no cap). We cap via .detail-card and
         scroll inside each pane instead. -->
    <v-dialog
        v-model="isOpen"
        :contained="contained"
        :max-width="contained ? '100%' : '90vw'"
        max-height="90vh"
        @update:model-value="handleClose"
    >
        <v-card class="detail-card">
            <!-- Toolbar -->
            <v-toolbar
                color="primary"
                dark
                class="flex-fixed"
            >
                <v-btn
                    icon
                    @click="isOpen = false"
                >
                    <v-icon>mdi-close-circle</v-icon>
                </v-btn>
                <v-toolbar-title class="truncate">
                    {{ title }}
                </v-toolbar-title>
                <v-spacer />

                <!-- Action Buttons -->
                <AssessItemActions
                    v-if="!multiSelectActive"
                    :item="newsItem"
                    :disabled="actionsDisabled"
                    size="small"
                    variant="text"
                    icon-size="small"
                    show-counts
                    show-create-report
                    :show-ungroup="isAggregate"
                    @action="handleDialogAction"
                />
            </v-toolbar>

            <!-- Tabs -->
            <v-tabs
                v-model="activeTab"
                dark
                density="compact"
                class="flex-fixed"
            >
                <!-- Single Item Tabs: Source, Attributes, Comments -->
                <template v-if="!isAggregate">
                    <v-tab value="source">
                        {{ t('assess.source') }}
                    </v-tab>
                    <v-tab value="attributes">
                        {{ t('assess.attributes') }}
                    </v-tab>
                    <v-tab value="comments">
                        {{ t('assess.comments') }}
                    </v-tab>
                </template>

                <!-- Aggregate Tabs: Info, Comments -->
                <template v-else>
                    <v-tab value="info">
                        {{ t('assess.aggregate_info') }}
                    </v-tab>
                    <v-tab value="comments">
                        {{ t('assess.comments') }}
                    </v-tab>
                </template>
            </v-tabs>

            <!-- Tab Content: every pane of the current mode is stacked in one grid cell, so
                 the area is as tall as the tallest tab and its height never changes when
                 switching tabs. Only the active pane is visible (toggled with visibility, so
                 hidden panes still reserve their space). -->
            <div class="bg-surface tab-content">
                <!-- Single Item: Source Tab -->
                <div
                    v-if="!isAggregate"
                    class="pane source-tab"
                    :class="{ 'pane--active': activeTab === 'source' }"
                >
                    <!-- Fixed header: metadata + article title stay pinned -->
                    <div class="source-header">
                        <v-row class="mb-6">
                            <v-col
                                cols="12"
                                md="3"
                                class="text-center"
                            >
                                <div class="text-overline font-weight-bold">
                                    {{ t('assess.collected') }}
                                </div>
                                <div class="text-caption">
                                    {{ firstNewsItemData?.collected || 'N/A' }}
                                </div>
                            </v-col>
                            <v-col
                                cols="12"
                                md="3"
                                class="text-center"
                            >
                                <div class="text-overline font-weight-bold">
                                    {{ t('assess.published') }}
                                </div>
                                <div class="text-caption">
                                    {{ firstNewsItemData?.published || 'N/A' }}
                                </div>
                            </v-col>
                            <v-col
                                cols="12"
                                md="3"
                                class="text-center"
                            >
                                <div class="text-overline font-weight-bold">
                                    {{ t('assess.source') }}
                                </div>
                                <div class="text-caption">
                                    {{ firstNewsItemData?.source || 'N/A' }}
                                </div>
                            </v-col>
                            <v-col
                                cols="12"
                                md="3"
                                class="text-center"
                            >
                                <div class="text-overline font-weight-bold">
                                    {{ t('assess.author') }}
                                </div>
                                <div class="text-caption">
                                    {{ firstNewsItemData?.author || 'N/A' }}
                                </div>
                            </v-col>
                        </v-row>

                        <v-divider />
                    </div>

                    <!-- Scrollable body: only the article content scrolls -->
                    <div class="source-body">
                        <div
                            class="text-body-2 text-medium-emphasis"
                            v-html="firstNewsItemData?.content"
                        />
                    </div>

                    <!-- Fixed footer: link stays pinned -->
                    <div
                        v-if="hasLink"
                        class="source-footer"
                    >
                        <v-divider class="mb-3" />
                        <div class="text-caption">
                            <strong>{{ t('assess.link') }}: </strong>
                            <a
                                :href="newsItemLink"
                                target="_blank"
                                rel="noreferrer"
                            >
                                {{ newsItemLink }}
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Single Item: Attributes Tab -->
                <div
                    v-if="!isAggregate"
                    class="pane tab-pane"
                    :class="{ 'pane--active': activeTab === 'attributes' }"
                >
                    <v-row>
                        <v-col
                            v-if="newsItemAttributes.length === 0"
                            cols="12"
                            class="text-center text-grey"
                        >
                            {{ t('common.no_data') }}
                        </v-col>
                        <v-col
                            v-for="attributeItem in newsItemAttributes"
                            :key="attributeItem.id"
                            cols="12"
                        >
                            <NewsItemAttribute
                                :attribute="attributeItem"
                                :news-item-data="firstNewsItemData"
                            />
                        </v-col>
                    </v-row>
                </div>

                <!-- Aggregate: Info Tab (Editable Form) -->
                <div
                    v-if="isAggregate"
                    class="pane tab-pane"
                    :class="{ 'pane--active': activeTab === 'info' }"
                >
                    <v-form>
                        <v-text-field
                            v-model="editTitle"
                            :label="t('assess.title')"
                            density="comfortable"
                            variant="outlined"
                            class="mb-4"
                            @blur="autoSaveAggregateInfo"
                        />
                        <v-textarea
                            v-model="editDescription"
                            :label="t('assess.description')"
                            density="comfortable"
                            variant="outlined"
                            rows="6"
                            class="mb-4"
                            @blur="autoSaveAggregateInfo"
                        />
                        <div class="text-caption text-grey">{{ t('assess.auto_save_blur') }}</div>
                    </v-form>
                </div>

                <!-- Comments Tab -->
                <div
                    class="pane tab-pane"
                    :class="{ 'pane--active': activeTab === 'comments' }"
                >
                    <Editor
                        v-model="commentText"
                        editor-style="height: 250px"
                        @text-change="debounceAutoSave"
                    />
                    <div class="text-caption text-grey mt-2">{{ t('assess.auto_save_changes') }}</div>
                </div>
            </div>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import Editor from 'primevue/editor'
    import AssessItemActions from '@/components/assess/AssessItemActions.vue'
    import NewsItemAttribute from '@/components/assess/NewsItemAttribute.vue'

    type NewsAttributeItem = {
        id: number | string
        attribute_group_item?: {
            attribute?: {
                type?: string
                [key: string]: unknown
            }
            [key: string]: unknown
        }
        [key: string]: any
    }

    type NewsItemData = {
        collected?: string
        published?: string
        source?: string
        author?: string
        title?: string
        content?: string
        link?: string
        attributes?: NewsAttributeItem[]
        [key: string]: any
    }

    type NestedNewsItem = {
        news_item_data?: NewsItemData
        [key: string]: any
    }

    type NewsItemModel = {
        id?: number | string
        title?: string
        description?: string
        comments?: string
        news_items?: NestedNewsItem[]
        [key: string]: any
    }

    type ActionPayload = {
        action: string
        newsItem: NewsItemModel
        comment?: string
        title?: string
        description?: string
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            newsItem?: NewsItemModel | null
            multiSelectActive?: boolean
            actionsDisabled?: boolean
            contained?: boolean
        }>(),
        {
            modelValue: false,
            newsItem: () => ({}),
            multiSelectActive: false,
            actionsDisabled: false,
            contained: false
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'action', payload: ActionPayload): void
        (e: 'delete', item: NewsItemModel): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const isOpen = ref<boolean>(false)
    const activeTab = ref<'source' | 'attributes' | 'comments' | 'info'>('source')
    const commentText = ref<string>('')
    const editTitle = ref<string>('')
    const editDescription = ref<string>('')
    let lastNewsItemId: number | string | null = null

    // Sync modelValue with local state
    watch(
        () => props.modelValue,
        (newVal: boolean) => {
            isOpen.value = newVal
        }
    )

    watch(isOpen, (newVal: boolean) => {
        emit('update:modelValue', newVal)
    })

    // Initialize edit fields when item changes
    watch(
        () => props.newsItem,
        (newItem: NewsItemModel) => {
            if (newItem) {
                // Only reset tab when switching to a different item, not on data refresh.
                // Aggregates have no "source" tab, so start them on "info".
                if (lastNewsItemId !== newItem.id) {
                    const isAgg = (newItem.news_items?.length || 0) > 1
                    activeTab.value = isAgg ? 'info' : 'source'
                    lastNewsItemId = newItem.id ?? null
                }
                editTitle.value = newItem.title || ''
                editDescription.value = newItem.description || ''
                // Pre-populate comment editor with existing comments
                commentText.value = newItem.comments || ''
            }
        }
    )

    const newsItem = computed<NewsItemModel>(() => props.newsItem || {})

    const isAggregate = computed(() => {
        return (newsItem.value.news_items?.length || 0) > 1
    })

    const title = computed(() => {
        if (isAggregate.value) {
            return t('assess.aggregate_detail')
        }
        return newsItem.value.title || ''
    })

    const firstNewsItemData = computed(() => {
        return newsItem.value.news_items?.[0]?.news_item_data || {}
    })

    const newsItemLink = computed(() => {
        return firstNewsItemData.value.link || ''
    })

    const hasLink = computed(() => {
        return !!newsItemLink.value
    })

    const newsItemAttributes = computed<NewsAttributeItem[]>(() => {
        const attributes: NewsAttributeItem[] = []
        if (newsItem.value.news_items) {
            newsItem.value.news_items.forEach((item: NestedNewsItem) => {
                if (item.news_item_data?.attributes) {
                    attributes.push(...item.news_item_data.attributes)
                }
            })
        }
        return attributes
    })

    const canCreateReport = computed(() => {
        return checkPermission(PERMISSIONS.ANALYZE_CREATE)
    })

    const canDelete = computed(() => {
        return checkPermission(PERMISSIONS.ASSESS_DELETE)
    })

    const handleClose = (): void => {
        isOpen.value = false
    }

    const handleDialogAction = (action: string): void => {
        if (action === 'delete') {
            handleDelete()
        } else {
            handleAction(action)
        }
    }

    const handleAction = (action: string): void => {
        emit('action', { action, newsItem: newsItem.value })
    }

    const handleDelete = (): void => {
        isOpen.value = false
        emit('delete', newsItem.value)
    }

    // Debounce timeout for auto-save
    let saveTimeout: ReturnType<typeof setTimeout> | null = null

    const debounceAutoSave = (): void => {
        if (saveTimeout) {
            clearTimeout(saveTimeout)
        }
        saveTimeout = setTimeout(() => {
            saveComment()
        }, 1000) // Save 1 second after the user stops typing
    }

    const saveComment = (): void => {
        emit('action', {
            action: 'comment',
            newsItem: newsItem.value,
            comment: commentText.value
        })
    }

    const autoSaveComment = (): void => {
        saveComment()
    }

    const autoSaveAggregateInfo = (): void => {
        // Only save if content has changed
        if (editTitle.value !== newsItem.value.title || editDescription.value !== newsItem.value.description) {
            saveAggregateInfo()
        }
    }

    const saveAggregateInfo = (): void => {
        emit('action', {
            action: 'update-aggregate',
            newsItem: newsItem.value,
            title: editTitle.value,
            description: editDescription.value
        })
    }

    const resetAggregateInfo = (): void => {
        editTitle.value = newsItem.value.title || ''
        editDescription.value = newsItem.value.description || ''
    }
</script>

<style scoped>
    /* ---- Dialog shell ----
       Column layout so the toolbar + tabs stay pinned. The card hugs its content up to
       90vh; beyond that the active pane scrolls internally (min-height: 300px keeps a
       stub item from collapsing). */
    .detail-card {
        display: flex;
        flex-direction: column;
        min-height: 300px;
        max-height: 90vh;
    }

    /* Toolbar and tabs hold their natural height and are never compressed. */
    .flex-fixed {
        flex: 0 0 auto;
    }

    /* Tab content area: a single-cell grid that every pane is stacked into, so its height
       equals the tallest pane and is identical on every tab. flex: 0 1 auto lets it hug
       that content but shrink (active pane then scrolls) when the card reaches 90vh. */
    .tab-content {
        display: grid;
        grid-template-rows: minmax(0, 1fr);
        flex: 0 1 auto;
        min-height: 0;
        overflow: hidden;
    }

    /* Every pane occupies the same grid cell; inactive panes stay in layout (so the cell
       keeps the tallest-tab height) but are hidden and non-interactive. */
    .pane {
        grid-area: 1 / 1;
        min-height: 0;
    }

    .pane:not(.pane--active) {
        visibility: hidden;
    }

    /* Standard padded pane (attributes / aggregate info / comments): scrolls as a whole. */
    .tab-pane {
        padding: 24px;
        overflow-y: auto;
    }

    /* ---- Source tab: pinned metadata header + footer link, scrolling body ----
       Grid stretch gives this pane the full cell height, so .source-body can scroll. */
    .source-tab {
        display: flex;
        flex-direction: column;
    }

    .source-header {
        flex: 0 0 auto;
        padding: 24px 24px 0;
    }

    /* flex-basis: auto (not 0) so a long article counts toward the dialog height, letting
       it grow to the 90vh cap; min-height: 0 lets it then shrink and scroll internally. */
    .source-body {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        padding: 8px 24px;
    }

    .source-footer {
        flex: 0 0 auto;
        padding: 0 24px 24px;
    }

    /* ---- Misc ---- */
    .truncate {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 600px;
    }

    /* PrimeVue / Quill comment editor. */
    :deep(.p-editor-container) {
        border-radius: 4px;
    }

    :deep(.ql-editor) {
        min-height: 200px;
        font-family: inherit;
        font-size: 14px;
    }
</style>
