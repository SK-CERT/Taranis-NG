import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAllProducts } from '@/api/publish'
import { getAllUserPublishingChannels } from '@/api/user'

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
    const products_publishing_channels = ref<ItemListState>(emptyListState())
    const multi_select = ref(false)
    const selection = ref<SelectableItem[]>([])
    const pendingNewProduct = ref<unknown | null>(null)

    // Getters
    const getProducts = computed(() => products.value || emptyListState())
    const getProductsPublishingChannels = computed(() => products_publishing_channels.value || emptyListState())
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

    async function loadUserPublishingChannels(_data: SearchFilter | Record<string, unknown>): Promise<ApiResponse<unknown>> {
        const response = (await getAllUserPublishingChannels()) as ApiResponse<ItemListState>
        products_publishing_channels.value = response.data || emptyListState()
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
        products_publishing_channels,
        multi_select,
        selection,
        pendingNewProduct,

        // Getters
        getProducts,
        getProductsPublishingChannels,
        getMultiSelect,
        getSelection,
        selectedProducts,

        // Actions
        loadProducts,
        loadUserPublishingChannels,
        multiSelect,
        select,
        deselect
    }
})
