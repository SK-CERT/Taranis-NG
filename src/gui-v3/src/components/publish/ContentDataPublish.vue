<template>
    <v-container
        id="selector_publish"
        fluid
        class="pa-2"
    >
        <TransitionGroup
            name="card-list"
            tag="div"
            class="w-100"
        >
            <component
                :is="currentCard"
                v-for="collection in collections"
                :key="collection.id"
                :card="collection"
                :multi-select-active="multiSelectActive"
                :preselected="isPreselected(collection.id)"
                @selection-change="handleSelectionChange(collection.id, $event)"
            />
        </TransitionGroup>
        <div
            v-intersect="infiniteScrolling"
            class="mt-4"
            style="min-height: 100px; display: flex; align-items: center; justify-content: center"
        >
            <div
                v-if="!dataLoaded"
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
                v-else
                class="text-caption text-grey"
            >
                {{ t('common.end_of_list') }}
            </div>
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted, onUnmounted, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { usePublishStore } from '@/stores/publish'
    import { getAllProductTypes } from '@/api/config'
    import CardProduct from './CardProduct.vue'
    import CardCompact from '@/components/common/CardCompact.vue'

    type ProductItem = {
        id: string | number
        product_type_id?: string | number
        product_type_name?: string
        [key: string]: unknown
    }

    type ProductType = {
        id: string | number
        title?: string
        [key: string]: unknown
    }

    type FilterState = {
        search: string
        range: string
        published: boolean | string
        sort: string
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
    const publishStore = usePublishStore()

    const collections = ref<ProductItem[]>([])
    const dataLoaded = ref(false)
    const filter = ref<FilterState>({
        search: '',
        range: 'ALL',
        published: 'ALL',
        sort: 'DATE_DESC'
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

        if (dataLoaded.value && isIntersecting && collections.value.length < totalCount) {
            updateData(true, false)
        }
    }

    const updateData = async (append = false, reloadAll = false): Promise<void> => {
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

            // Load product types
            const productTypesResponse = await getAllProductTypes({ search: '' })
            const productTypes = Array.isArray(productTypesResponse?.data?.items) ? (productTypesResponse.data.items as ProductType[]) : []

            const newItems = Array.isArray(publishStore.getProducts.items) ? (publishStore.getProducts.items as ProductItem[]) : []

            if (Array.isArray(newItems) && Array.isArray(productTypes)) {
                for (let i = 0; i < newItems.length; i++) {
                    const item = newItems[i]
                    if (!item) {
                        continue
                    }
                    const productType = productTypes.find((x) => x.id == item.product_type_id)
                    if (productType) {
                        item.product_type_name = String(productType.title || 'Product')
                    } else {
                        item.product_type_name = 'Product'
                    }
                }
            }

            // Directly assign or concat - Vue will detect removed items and animate them
            if (append) {
                collections.value = collections.value.concat(newItems)
            } else {
                collections.value = newItems
            }

            emit('update-showing-count', collections.value.length)

            setTimeout(() => {
                dataLoaded.value = true
            }, 1000)
        } catch (error) {
            console.error('Error loading products:', error)
            dataLoaded.value = true
        }
    }

    const handleFilterUpdate = (event: Event): void => {
        const customEvent = event as CustomEvent<FilterState>
        filter.value = customEvent.detail
        updateData(false, false)
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

    const handleProductUpdate = (): void => {
        // Reload current view after product update/deletion
        // The animation will trigger when the deleted item is missing from the new data
        updateData(false, true)
    }

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
