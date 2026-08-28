import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAllProducts, getPublishPublicWebs } from '@/api/publish'
import { getAllUserPublishersPresets } from '@/api/user'

type SearchFilter = {
    search: string
}

type ItemListState = {
    total_count: number
    items: unknown[]
}

type SelectableItem = {
    id: string | number
    [key: string]: unknown
}

type ApiResponse<T> = {
    data?: T
}

type PublicWebOption = {
    id: number | string
    name: string
}

type PublicWebsState = {
    total_count: number
    items: PublicWebOption[]
}

const emptyListState = (): ItemListState => ({ total_count: 0, items: [] })

export const usePublishStore = defineStore('publish', () => {
    // State
    const products = ref<ItemListState>(emptyListState())
    const products_publisher_presets = ref<ItemListState>(emptyListState())
    const multi_select = ref(false)
    const selection = ref<SelectableItem[]>([])
    const pendingNewProduct = ref<unknown | null>(null)
    const publicWebOptions = ref<PublicWebOption[]>([])
    const publicWebOptionsLoaded = ref(false)
    // Memo of the in-flight fetch so concurrent callers (e.g. two rapid NewProduct
    // mounts) share one request instead of firing two.
    let publicWebOptionsFetch: Promise<void> | null = null

    // Getters
    const getProducts = computed(() => products.value || emptyListState())
    const getProductsPublisherPresets = computed(() => products_publisher_presets.value || emptyListState())
    const getMultiSelect = computed(() => multi_select.value)
    const getSelection = computed(() => selection.value)
    const selectedProducts = computed(() => {
        return new Set(selection.value.map((item) => item.id))
    })
    // The "any public web exists" flag (the GUI's public-web gate). This is NOT
    // NewProduct's choice predicate (publicWebOptions.length > 1 in
    // NewProduct.vue, which only shows the target selector when there is a
    // choice); kept as the store's public API.
    const publicWebEnabled = computed(() => publicWebOptions.value.length > 0)

    // Actions
    async function loadProducts(data: SearchFilter | Record<string, unknown>): Promise<ApiResponse<unknown>> {
        const response = (await getAllProducts(data)) as ApiResponse<ItemListState>
        if (response) {
            products.value = response.data || emptyListState()
        }
        return response
    }

    async function loadUserPublishersPresets(_data: SearchFilter | Record<string, unknown>): Promise<ApiResponse<unknown>> {
        const response = (await getAllUserPublishersPresets()) as ApiResponse<ItemListState>
        products_publisher_presets.value = response.data || emptyListState()
        return response
    }

    // The Publish view is the only regular consumer, so the options are cached;
    // a failed request stays unmarked and is retried on the next load. Call
    // `invalidatePublicWebOptions()` whenever a public web is created, updated
    // or deleted (config flows, SSE resync) so the cache cannot serve a web
    // that no longer exists — a stale id saved into a product would silently
    // drop on the backend and turn the product global.
    async function loadPublicWebOptions(): Promise<void> {
        if (publicWebOptionsLoaded.value) {
            return
        }
        if (publicWebOptionsFetch === null) {
            publicWebOptionsFetch = (async () => {
                try {
                    const response = (await getPublishPublicWebs()) as ApiResponse<PublicWebsState>
                    publicWebOptions.value = response.data?.items || []
                    publicWebOptionsLoaded.value = true
                } catch (error: unknown) {
                    console.error('Failed to load public-web websites:', error)
                } finally {
                    publicWebOptionsFetch = null
                }
            })()
        }
        await publicWebOptionsFetch
    }

    function invalidatePublicWebOptions(): void {
        publicWebOptionsFetch = null
        publicWebOptionsLoaded.value = false
        publicWebOptions.value = []
    }

    // Invalidation on its own leaves the options empty until something loads them
    // again. Callers that stay mounted (the Publish view's SSE resync) must use
    // this instead: the product dialog reads the options only when it is mounted,
    // so an empty list there hides the target selector and lets a new product be
    // saved with no targeting at all - which the backend treats as "every web".
    async function refreshPublicWebOptions(): Promise<void> {
        invalidatePublicWebOptions()
        await loadPublicWebOptions()
    }

    function multiSelect(enable: boolean): void {
        multi_select.value = enable
        selection.value = []
    }

    function select(selected_item: SelectableItem): void {
        selection.value.push(selected_item)
    }

    function deselect(selectedItem: SelectableItem): void {
        for (let i = 0; i < selection.value.length; i++) {
            const item = selection.value[i]
            if (item && item.id === selectedItem.id) {
                selection.value.splice(i, 1)
                break
            }
        }
    }

    return {
        // State
        products,
        products_publisher_presets,
        multi_select,
        selection,
        pendingNewProduct,
        publicWebOptions,

        // Getters
        getProducts,
        getProductsPublisherPresets,
        getMultiSelect,
        getSelection,
        selectedProducts,
        publicWebEnabled,

        // Actions
        loadProducts,
        loadUserPublishersPresets,
        loadPublicWebOptions,
        invalidatePublicWebOptions,
        refreshPublicWebOptions,
        multiSelect,
        select,
        deselect
    }
})
