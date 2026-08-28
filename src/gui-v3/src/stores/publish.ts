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

    // The Publish view is the only consumer, so one fetch per session is enough;
    // a failed request stays unmarked and is retried on the next mount.
    async function loadPublicWebOptions(): Promise<void> {
        if (publicWebOptionsLoaded.value) {
            return
        }
        try {
            const response = (await getPublishPublicWebs()) as ApiResponse<PublicWebsState>
            publicWebOptions.value = response.data?.items || []
            publicWebOptionsLoaded.value = true
        } catch (error: unknown) {
            console.error('Failed to load public-web websites:', error)
        }
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
        multiSelect,
        select,
        deselect
    }
})
