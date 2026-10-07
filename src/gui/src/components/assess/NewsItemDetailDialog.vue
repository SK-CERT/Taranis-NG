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
                    <bdi dir="auto">{{ title }}</bdi>
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
                show-arrows
                class="flex-fixed"
            >
                <!-- Aggregate Tabs: Info -->
                <template v-if="isAggregate">
                    <v-tab value="info">
                        {{ t('assess.aggregate_info') }}
                    </v-tab>
                </template>

                <!-- Single Item Tabs: Source (or one tab per version, newest first), Attributes -->
                <template v-else>
                    <v-tab
                        value="source"
                        data-test="source-tab"
                    >
                        <template v-if="currentVersion">
                            {{ t('assess.current_version_label', { version: currentVersion }) }}
                        </template>
                        <template v-else>
                            {{ t('assess.source') }}
                        </template>
                    </v-tab>
                    <v-tab
                        v-for="version in olderVersions"
                        :key="versionTab(version)"
                        :value="versionTab(version)"
                        data-test="version-tab"
                    >
                        {{ t('assess.version_label', { version: version.version || '' }) }}
                    </v-tab>
                    <v-tab value="attributes">
                        {{ t('assess.attributes') }}
                    </v-tab>
                </template>
                <!-- Disable comments for child items -->
                <v-tab
                    v-if="!isChild"
                    value="comments"
                >
                    {{ t('assess.comments') }}
                </v-tab>
            </v-tabs>

            <!-- Tab Content: every pane of the current mode is stacked in one grid cell, so
                 the area is as tall as the tallest tab and its height never changes when
                 switching tabs. Only the active pane is visible (toggled with visibility, so
                 hidden panes still reserve their space). -->
            <div class="bg-surface tab-content">
                <!-- Single Item: Source Tab (the current version of a versioned item) -->
                <NewsItemSourcePane
                    v-if="!isAggregate"
                    class="pane"
                    :class="{ 'pane--active': activeTab === 'source' }"
                    :collected="firstNewsItemData.collected"
                    :published="firstNewsItemData.published"
                    :source="firstNewsItemData.source"
                    :author="firstNewsItemData.author"
                    :content="firstNewsItemData.content"
                    :link="firstNewsItemData.link"
                />

                <!-- Single Item: older versions, rendered once opened -->
                <template v-if="!isAggregate">
                    <NewsItemSourcePane
                        v-for="version in renderedVersions"
                        :key="versionTab(version)"
                        class="pane"
                        :class="{ 'pane--active': activeTab === versionTab(version) }"
                        :collected="version.collected"
                        :published="version.published"
                        :source="firstNewsItemData.source"
                        :author="version.author"
                        :content="version.content"
                        :link="version.link"
                        :superseded="version.superseded"
                    />
                </template>

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
                            :spellcheck="spellcheck"
                            :label="t('assess.title')"
                            density="comfortable"
                            variant="outlined"
                            class="mb-4"
                            :readonly="!canModifyItem"
                            @blur="autoSaveAggregateInfo"
                        />
                        <v-textarea
                            v-model="editDescription"
                            :spellcheck="spellcheck"
                            :label="t('assess.description')"
                            density="comfortable"
                            variant="outlined"
                            rows="6"
                            class="mb-4"
                            :readonly="!canModifyItem"
                            @blur="autoSaveAggregateInfo"
                        />
                        <div class="text-caption text-grey">{{ t('assess.auto_save_blur') }}</div>
                    </v-form>
                </div>

                <!-- Comments Tab -->
                <div
                    v-if="!isChild"
                    class="pane tab-pane"
                    :class="{ 'pane--active': activeTab === 'comments' }"
                >
                    <Editor
                        v-model="commentText"
                        :pt="editorPassThrough"
                        editor-style="height: 250px; font-size: 16px;"
                        :readonly="!canModifyItem"
                        @text-change="autoSaveComment"
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
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import Editor from 'primevue/editor'
    import AssessItemActions from '@/components/assess/AssessItemActions.vue'
    import NewsItemAttribute from '@/components/assess/NewsItemAttribute.vue'
    import NewsItemSourcePane from '@/components/assess/NewsItemSourcePane.vue'
    import { getNewsItemVersions } from '@/api/assess'
    import { Action, type ActionKey } from '@/types/actions'

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
        id?: string
        hash?: string
        collected?: string
        published?: string
        source?: string
        author?: string
        title?: string
        content?: string
        link?: string
        /** The provider's label for the revision held, set only for versioned items. */
        version?: string | null
        attributes?: NewsAttributeItem[]
        [key: string]: any
    }

    /** One revision of a versioned item, as GET /assess/news-items/<id>/versions returns it. */
    type NewsItemVersion = {
        id: number | null
        version?: string | null
        title?: string
        review?: string
        content?: string
        link?: string
        published?: string
        author?: string
        collected?: string
        superseded?: string | null
        current?: boolean
    }

    type VersionTab = `version-${number}`
    type TabValue = 'source' | 'attributes' | 'comments' | 'info' | VersionTab

    type NestedNewsItem = {
        id?: number | string
        news_item_data?: NewsItemData
        [key: string]: any
    }

    type NewsItemModel = {
        id?: number | string
        entityType?: 'news_item' | 'news_item_aggregate'
        title?: string
        description?: string
        comments?: string
        modify?: boolean
        news_items?: NestedNewsItem[]
        [key: string]: any
    }

    type ActionPayload = {
        action: ActionKey
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
    const spellcheck = useSpellcheck()
    const editorPassThrough = computed(() => ({ content: { spellcheck: spellcheck.value } }))

    const isOpen = ref<boolean>(false)
    const activeTab = ref<TabValue>('source')
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
                    visitedVersionTabs.value = new Set()
                }
                editTitle.value = newItem.title || ''
                editDescription.value = newItem.description || ''
                // Pre-populate comment editor with existing comments
                commentText.value = newItem.comments || ''
            }
        }
    )

    const newsItem = computed<NewsItemModel>(() => props.newsItem || {})

    // checks if multiple items (> 1) are grouped into one record, not if it's aggregate type record (master)
    const isAggregate = computed(() => {
        return (newsItem.value.news_items?.length || 0) > 1
    })

    const isChild = computed(() => {
        return newsItem.value.entityType === 'news_item'
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

    // ---- Versions ----
    // A versioned item (e.g. a CSAF advisory) shows one tab per revision: the current one
    // from the item itself, the older ones fetched when the dialog opens.
    const currentVersion = computed(() => firstNewsItemData.value.version || '')
    const olderVersions = ref<NewsItemVersion[]>([])
    const visitedVersionTabs = ref<Set<VersionTab>>(new Set())
    let loadedVersionsKey = ''

    const versionTab = (version: NewsItemVersion): VersionTab => `version-${version.id ?? 0}`

    // Older versions render once opened, then stay: a long history would otherwise put every
    // revision's full text in the page at once.
    const renderedVersions = computed(() => olderVersions.value.filter((version) => visitedVersionTabs.value.has(versionTab(version))))

    watch(activeTab, (tab: TabValue) => {
        if (tab.startsWith('version-')) {
            visitedVersionTabs.value.add(tab as VersionTab)
        }
    })

    const loadVersions = async (): Promise<void> => {
        // The versions belong to the news item, not to the aggregate wrapping it.
        const newsItemId = newsItem.value.news_items?.[0]?.id
        const open = props.modelValue || isOpen.value
        if (!open || isAggregate.value || !currentVersion.value || newsItemId === undefined || newsItemId === null) {
            olderVersions.value = []
            loadedVersionsKey = ''
            return
        }
        // Keyed by the revision held, so a newer revision arriving (SSE refresh) reloads them.
        const key = `${newsItemId}:${firstNewsItemData.value.id ?? ''}:${firstNewsItemData.value.hash ?? ''}`
        if (key === loadedVersionsKey) {
            return
        }
        loadedVersionsKey = key
        olderVersions.value = []
        visitedVersionTabs.value = new Set()
        if (activeTab.value.startsWith('version-')) {
            activeTab.value = 'source'
        }
        try {
            const response = await getNewsItemVersions(newsItemId)
            if (key !== loadedVersionsKey) {
                return
            }
            const items: NewsItemVersion[] = response?.data?.items || []
            olderVersions.value = items.filter((version) => !version.current)
        } catch {
            // Not allowed or not reachable (e.g. from the Analyze selector): the current
            // version is still shown, just without its history.
            if (key === loadedVersionsKey) {
                olderVersions.value = []
            }
        }
    }

    watch(
        () => [
            props.modelValue,
            isOpen.value,
            newsItem.value.news_items?.[0]?.id,
            firstNewsItemData.value.id,
            firstNewsItemData.value.hash,
            currentVersion.value
        ],
        () => {
            void loadVersions()
        },
        { immediate: true }
    )

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

    const canModifyItem = computed(() => {
        const itemAllowsModification = newsItem.value.entityType !== 'news_item' || newsItem.value.modify === true
        return checkPermission(PERMISSIONS.ASSESS_UPDATE) && itemAllowsModification
    })

    const handleClose = (): void => {
        isOpen.value = false
    }

    const handleDialogAction = (action: ActionKey): void => {
        if (action === Action.DELETE) {
            handleDelete()
        } else {
            handleAction(action)
        }
    }

    const handleAction = (action: ActionKey): void => {
        emit('action', { action, newsItem: newsItem.value })
    }

    const handleDelete = (): void => {
        isOpen.value = false
        emit('delete', newsItem.value)
    }

    // timeout for auto-save
    let saveTimeout: ReturnType<typeof setTimeout> | null = null

    const autoSaveComment = (): void => {
        if (!canModifyItem.value || isChild.value) {
            return
        }
        if (saveTimeout) {
            clearTimeout(saveTimeout)
        }
        saveTimeout = setTimeout(() => {
            emit('action', {
                action: Action.COMMENT,
                newsItem: newsItem.value,
                comment: commentText.value
            })
        }, 1000) // Save 1 second after the user stops typing
    }

    const autoSaveAggregateInfo = (): void => {
        if (!canModifyItem.value || !isAggregate.value) {
            return
        }
        // Only save if content has changed
        if (editTitle.value !== newsItem.value.title || editDescription.value !== newsItem.value.description) {
            emit('action', {
                action: Action.UPDATE_AGGREGATE,
                newsItem: newsItem.value,
                title: editTitle.value,
                description: editDescription.value
            })
        }
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

    /* ---- Misc ---- */
    .truncate {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 600px;
    }
</style>
