<template>
    <!-- contained renders the dialog inside its positioned ancestor (e.g. the side-by-side
         right column) instead of as a centered, full-screen-overlay modal. -->
    <v-dialog
        v-model="isOpen"
        :contained="contained"
        :max-width="contained ? '100%' : '90vw'"
        max-height="90vh"
        scrollable
        @update:model-value="handleClose"
    >
        <v-card style="min-height: 70vh; display: flex; flex-direction: column">
            <!-- Toolbar -->
            <v-toolbar color="primary" dark>
                <v-btn icon @click="isOpen = false">
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
            <v-tabs v-model="activeTab" dark density="compact">
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

            <!-- Tab Content -->
            <v-window v-model="activeTab" class="bg-surface" style="flex: 1; overflow-y: auto">
                <!-- Single Item: Source Tab -->
                <v-window-item v-if="!isAggregate" value="source" style="padding: 24px">
                    <v-row class="mb-6">
                        <v-col cols="12" md="3" class="text-center">
                            <div class="text-overline font-weight-bold">
                                {{ t('assess.collected') }}
                            </div>
                            <div class="text-caption">
                                {{ firstNewsItemData?.collected || 'N/A' }}
                            </div>
                        </v-col>
                        <v-col cols="12" md="3" class="text-center">
                            <div class="text-overline font-weight-bold">
                                {{ t('assess.published') }}
                            </div>
                            <div class="text-caption">
                                {{ firstNewsItemData?.published || 'N/A' }}
                            </div>
                        </v-col>
                        <v-col cols="12" md="3" class="text-center">
                            <div class="text-overline font-weight-bold">
                                {{ t('assess.source') }}
                            </div>
                            <div class="text-caption">
                                {{ firstNewsItemData?.source || 'N/A' }}
                            </div>
                        </v-col>
                        <v-col cols="12" md="3" class="text-center">
                            <div class="text-overline font-weight-bold">
                                {{ t('assess.author') }}
                            </div>
                            <div class="text-caption">
                                {{ firstNewsItemData?.author || 'N/A' }}
                            </div>
                        </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <div class="text-h5 font-weight-light mb-4">
                        {{ firstNewsItemData?.title || 'N/A' }}
                    </div>

                    <div class="text-body-2 text-medium-emphasis mb-4" v-html="firstNewsItemData?.content" />

                    <v-divider class="my-4" />

                    <div v-if="hasLink" class="text-caption">
                        <strong>Link: </strong>
                        <a :href="newsItemLink" target="_blank" rel="noreferrer">
                            {{ newsItemLink }}
                        </a>
                    </div>
                </v-window-item>

                <!-- Single Item: Attributes Tab -->
                <v-window-item v-if="!isAggregate" value="attributes" style="padding: 24px">
                    <v-row>
                        <v-col v-if="newsItemAttributes.length === 0" cols="12" class="text-center text-grey">
                            {{ t('common.no_data') }}
                        </v-col>
                        <v-col v-for="attributeItem in newsItemAttributes" :key="attributeItem.id" cols="12">
                            <!-- Use new AttributeContainer component for structured attribute displays -->
                            <AttributeContainer :attribute-item="attributeItem" :report-item-id="Number(newsItem.id || 0)" read-only />
                        </v-col>
                    </v-row>
                </v-window-item>

                <!-- Aggregate: Info Tab (Editable Form) -->
                <v-window-item v-if="isAggregate" value="info" style="padding: 24px">
                    <v-form class="min-width-600">
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
                        <div class="text-caption text-grey">Auto-saves on blur</div>
                    </v-form>
                </v-window-item>

                <!-- Comments Tab -->
                <v-window-item value="comments" style="padding: 24px">
                    <Editor v-model="commentText" editor-style="height: 250px" @text-change="debounceAutoSave" />
                    <div class="text-caption text-grey mt-2">Auto-saves on changes</div>
                </v-window-item>
            </v-window>
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
    import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'

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
                // Only reset tab when switching to a different item, not on data refresh
                if (lastNewsItemId !== newItem.id) {
                    activeTab.value = 'source'
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
    .truncate {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 600px;
    }

    .max-width-600 {
        max-width: 600px;
    }

    .gap-2 {
        gap: 8px;
    }

    :deep(.p-editor-container) {
        border-radius: 4px;
    }

    :deep(.ql-editor) {
        min-height: 200px;
        font-family: inherit;
        font-size: 14px;
    }
</style>
