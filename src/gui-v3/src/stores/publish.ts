import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAllProducts } from '@/api/publish'
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

const emptyListState = (): ItemListState => ({ total_count: 0, items: [] })

export const usePublishStore = defineStore('publish', () => {
    // State
    const products = ref<ItemListState>(emptyListState())
    const products_publisher_presets = ref<ItemListState>(emptyListState())
    const multi_select = ref(false)
    const selection = ref<SelectableItem[]>([])
    const pendingNewProduct = ref<unknown | null>(null)

    // Getters
    const getProducts = computed(() => products.value || emptyListState())
    const getProductsPublisherPresets = computed(() => products_publisher_presets.value || emptyListState())
    const getMultiSelect = computed(() => multi_select.value)
    const getSelection = computed(() => selection.value)
    const selectedProducts = computed(() => {
        return new Set(selection.value.map((item) => item.id))
    })

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

        // Getters
        getProducts,
        getProductsPublisherPresets,
        getMultiSelect,
        getSelection,
        selectedProducts,

        // Actions
        loadProducts,
        loadUserPublishersPresets,
        multiSelect,
        select,
        deselect
    }
})
