import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getAllProducts } from '@/api/publish'
import { getAllUserPublishersPresets } from '@/api/user'

export const usePublishStore = defineStore('publish', () => {
  // State
  const products = ref({ total_count: 0, items: [] })
  const products_publisher_presets = ref({ total_count: 0, items: [] })
  const multi_select = ref(false)
  const selection = ref([])
  const pendingNewProduct = ref(null)

  // Getters
  const getProducts = computed(() => products.value || { total_count: 0, items: [] })
  const getProductsPublisherPresets = computed(
    () => products_publisher_presets.value || { total_count: 0, items: [] }
  )
  const getMultiSelect = computed(() => multi_select.value)
  const getSelection = computed(() => selection.value)
  const selectedProducts = computed(() => {
    return new Set(selection.value.map((item) => item.id))
  })

  // Actions
  async function loadProducts(data) {
    const response = await getAllProducts(data)
    if (response) {
      products.value = response.data || { total_count: 0, items: [] }
    }
    return response
  }

  async function loadUserPublishersPresets(data) {
    const response = await getAllUserPublishersPresets(data)
    products_publisher_presets.value = response.data || { total_count: 0, items: [] }
    return response
  }

  function multiSelect(enable) {
    multi_select.value = enable
    selection.value = []
  }

  function select(selected_item) {
    selection.value.push(selected_item)
  }

  function deselect(selectedItem) {
    for (let i = 0; i < selection.value.length; i++) {
      if (selection.value[i].id === selectedItem.id) {
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
