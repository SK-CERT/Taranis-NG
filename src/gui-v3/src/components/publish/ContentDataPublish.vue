<template>
  <v-container id="selector_publish" fluid>
    <TransitionGroup name="card-list" tag="div" class="w-100">
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
    <div v-intersect="infiniteScrolling" class="mt-4" style="min-height: 100px; display: flex; align-items: center; justify-content: center">
      <div v-if="!dataLoaded" class="text-center text-grey">
        <v-progress-circular indeterminate size="small" />
        <p class="text-caption mt-2">{{ t('common.loading_more') }}</p>
      </div>
      <div v-else class="text-caption text-grey">
        {{ t('common.end_of_list') }}
      </div>
    </div>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePublishStore } from '@/stores/publish'
import { getAllProductTypes } from '@/api/config'
import CardProduct from './CardProduct.vue'
import CardCompact from '@/components/common/CardCompact.vue'

const props = defineProps({
  selection: Array
})

const emit = defineEmits(['update-showing-count'])

const { t } = useI18n()
const publishStore = usePublishStore()

const collections = ref([])
const dataLoaded = ref(false)
const filter = ref({
  search: '',
  range: 'ALL',
  published: false,
  unpublished: true,
  sort: 'DATE_DESC'
})

const currentCard = computed(() => {
  return filter.value.compact_mode ? CardCompact : CardProduct
})

const multiSelectActive = computed(() => publishStore.getMultiSelect)

const isPreselected = (item_id) => {
  if (props.selection) {
    return props.selection.some((item) => item.id === item_id)
  }
  return false
}

const infiniteScrolling = (entries) => {
  if (dataLoaded.value && entries?.[0]?.isIntersecting) {
    updateData(true, false)
  }
}

const updateData = async (append, reloadAll) => {
  dataLoaded.value = false

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
    const productTypes = productTypesResponse?.data?.items || []

    const newItems = publishStore.getProducts.items || []

    if (Array.isArray(newItems) && Array.isArray(productTypes)) {
      for (let i = 0; i < newItems.length; i++) {
        const productType = productTypes.find((x) => x.id == newItems[i].product_type_id)
        if (productType) {
          newItems[i].product_type_name = productType.title
        } else {
          newItems[i].product_type_name = 'Product'
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

const handleFilterUpdate = (event) => {
  filter.value = event.detail
  updateData(false, false)
}

const handleSelectionChange = (itemId, isSelected) => {
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

const handleProductUpdate = () => {
  // Reload current view after product update/deletion
  // The animation will trigger when the deleted item is missing from the new data
  updateData(false, true)
}

onMounted(() => {
  updateData(false, false)
  window.addEventListener('update-products-filter', handleFilterUpdate)
  window.addEventListener('product-updated', handleProductUpdate)
})

onUnmounted(() => {
  window.removeEventListener('update-products-filter', handleFilterUpdate)
  window.removeEventListener('product-updated', handleProductUpdate)
})

defineExpose({
  updateData
})
</script>
