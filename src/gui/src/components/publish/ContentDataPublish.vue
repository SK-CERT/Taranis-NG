<template>
    <v-container
        id="selector_publish"
        fluid
        class="pa-0"
    >
        <ContentSkeleton
            v-if="!dataLoaded && collections.length === 0"
            :compact="currentCard === CardCompact"
            variant="product"
        />
        <div class="publish-list w-100">
            <component
                :is="currentCard"
                v-for="collection in collections"
                :key="collection.id"
                :card="collection"
                :multi-select-active="multiSelectActive"
                :preselected="isPreselected(collection.id)"
                @selection-change="handleSelectionChange(collection.id, $event)"
                @show-detail="openProduct"
                @edit="openProduct"
            />
        </div>
        <div
            v-intersect="infiniteScrolling"
            class="mt-4"
            style="min-height: 100px; display: flex; align-items: center; justify-content: center"
        >
            <div
                v-if="!dataLoaded && collections.length > 0"
                class="text-center text-grey"
            >
                <v-progress-circular
                    indeterminate
                    size="small"
                />
                <p class="text-caption mt-2">
                    {{ t('common.loading_more') }}
                </p>
            </div>
            <div
                v-else-if="collections.length > 0"
                class="text-caption text-grey"
            >
                {{ t('common.end_of_list') }}
            </div>
        </div>

        <!-- Empty State -->
        <v-row
            v-if="dataLoaded && collections.length === 0"
            justify="center"
            class="my-8"
        >
            <v-col
                cols="12"
                md="6"
                class="text-center"
            >
                <v-icon
                    size="64"
                    color="grey"
                >
                    {{ ICONS.SEND_OUTLINE }}
                </v-icon>
                <p class="text-h6 text-grey mt-4">
                    {{ t('publish.no_items') }}
                </p>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted, onUnmounted, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { ICONS } from '@/config/ui-constants'
    import { tagFilterQuery, type TagFilterState } from '@/api/tags'
    import { usePublishStore } from '@/stores/publish'
    import { routeProductPresetId } from '@/types/product-presets'
    import CardProduct from './CardProduct.vue'
    import ContentSkeleton from '@/components/common/ContentSkeleton.vue'
    import CardCompact from '@/components/common/CardCompact.vue'
    import { useSseResync } from '@/composables/useSseResync'

    type ProductItem = {
        id: string | number
        product_preset_id?: string | number
        product_preset_name?: string
        [key: string]: unknown
    }

    type FilterState = TagFilterState & {
        search: string
        range: string
        published: boolean | string
        sort: string
        product_preset_id?: number | null
        compact_mode?: boolean
    }

    const props = withDefaults(
        defineProps<{
            selection?: Array<{ id: string | number }>
        }>(),
        {
            selection: () => []
        }
    )

    const emit = defineEmits(['update-showing-count'])

    const { t } = useI18n()
    const route = useRoute()
    const publishStore = usePublishStore()

    const collections = ref<ProductItem[]>([])
    const dataLoaded = ref(false)
    let updateSequence = 0
    // The first load runs before the toolbar's filter arrives, so it takes the sidebar's product preset itself.
    const filter = ref<FilterState>({
        search: '',
        range: 'ALL',
        published: 'ALL',
        sort: 'DATE_DESC',
        product_preset_id: routeProductPresetId(route.params)
    })

    const currentCard = computed(() => {
        return filter.value.compact_mode ? CardCompact : CardProduct
    })

    const multiSelectActive = computed(() => publishStore.getMultiSelect)

    const isPreselected = (item_id: string | number): boolean => props.selection.some((item) => item.id === item_id)

    const infiniteScrolling = (entries: boolean | IntersectionObserverEntry[] | IntersectionObserverEntry): void => {
        const isIntersecting =
            typeof entries === 'boolean'
                ? entries
                : Array.isArray(entries)
                  ? entries[0]?.isIntersecting === true
                  : entries?.isIntersecting === true

        const totalCount = publishStore.getProducts.total_count || 0
        // Don't attempt to load more when there are no items to load
        if (totalCount === 0) {
            return
        }

        if (dataLoaded.value && isIntersecting && collections.value.length < totalCount) {
            updateData(true, false)
        }
    }

    const updateData = async (append = false, reloadAll = false): Promise<void> => {
        const requestId = ++updateSequence
        dataLoaded.value = false

        const totalCount = publishStore.getProducts.total_count || 0
        if (append && totalCount > 0 && collections.value.length >= totalCount) {
            dataLoaded.value = true
            return
        }

        let offset = collections.value.length
        let limit = 20
        if (reloadAll) {
            offset = 0
            if (collections.value.length > limit) {
                limit = collections.value.length
            }
        } else if (append === false) {
            offset = 0
        }

        try {
            await publishStore.loadProducts({
                filter: filter.value,
                offset: offset,
                limit: limit
            })

            if (requestId !== updateSequence) {
                return
            }

            const newItems = Array.isArray(publishStore.getProducts.items) ? (publishStore.getProducts.items as ProductItem[]) : []

            // Directly assign or concat - Vue will detect removed items and animate them
            if (append) {
                const existingIds = new Set(collections.value.map((item) => String(item.id)))
                collections.value = collections.value.concat(newItems.filter((item) => !existingIds.has(String(item.id))))
            } else {
                collections.value = newItems
            }

            emit('update-showing-count', collections.value.length)
        } catch (error) {
            console.error('Error loading products:', error)
        } finally {
            if (requestId === updateSequence) {
                dataLoaded.value = true
            }
        }
    }

    const handleFilterUpdate = (event: Event): void => {
        const customEvent = event as CustomEvent<FilterState>
        const oldFilter = filter.value
        const newFilter = customEvent.detail
        const dataFilterChanged =
            oldFilter.search !== newFilter.search ||
            oldFilter.range !== newFilter.range ||
            oldFilter.published !== newFilter.published ||
            oldFilter.sort !== newFilter.sort ||
            tagFilterQuery(oldFilter) !== tagFilterQuery(newFilter) ||
            (oldFilter.product_preset_id ?? null) !== (newFilter.product_preset_id ?? null)

        filter.value = newFilter
        if (dataFilterChanged) {
            updateData(false, false)
        }
    }

    const handleSelectionChange = (itemId: string | number, isSelected: boolean): void => {
        // Get the full item from collections
        const item = collections.value.find((c) => c.id === itemId)
        if (item) {
            if (isSelected) {
                publishStore.select({ id: itemId, item: item })
            } else {
                publishStore.deselect({ id: itemId })
            }
        }
    }

    const openProduct = (product: ProductItem): void => {
        const state = product['state'] as { id?: string | number | null } | null | undefined
        window.dispatchEvent(
            new CustomEvent('show-product-edit', {
                detail: {
                    id: product.id,
                    title: product['title'],
                    description: product['subtitle'] || '',
                    product_preset_id: product.product_preset_id,
                    state_id: state?.id || null,
                    report_items: product['report_items'] || [],
                    modify: product['modify'] === true,
                    access: product['access'] === true
                }
            })
        )
    }

    const handleProductUpdate = (): void => {
        // Reload current view after product update/deletion
        // The animation will trigger when the deleted item is missing from the new data
        updateData(false, true)
    }

    useSseResync(async () => {
        await updateData(false, true)
    })

    onMounted(() => {
        updateData(false, false)
        window.addEventListener('update-products-filter', handleFilterUpdate as EventListener)
        window.addEventListener('product-updated', handleProductUpdate as EventListener)
    })

    onUnmounted(() => {
        window.removeEventListener('update-products-filter', handleFilterUpdate as EventListener)
        window.removeEventListener('product-updated', handleProductUpdate as EventListener)
    })

    defineExpose({
        updateData
    })
</script>

<style scoped>
    #selector_publish {
        width: 100%;
        max-width: none;
        padding: 0 !important;
    }

    .publish-list {
        display: grid;
        width: 100%;
        gap: 0;
    }
</style>
