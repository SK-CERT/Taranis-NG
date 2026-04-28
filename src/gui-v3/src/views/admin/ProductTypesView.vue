<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.product_types"
      :total-count="configStore.productTypes.total_count"
      total-count-title="product_type.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewProductType :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.productTypes.items"
      card-item="CardCompact"
      delete-permission="CONFIG_PRODUCT_TYPE_DELETE"
      :loading="loading"
      @delete="handleDelete"
      @edit="handleEdit"
      @refresh="loadData"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { deleteProductType } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewProductType from '@/components/config/product-types/NewProductType.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadProductTypes(filter.value)
  } catch (error) {
    console.error('Error loading product types:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (productType) => {
  try {
    await deleteProductType(productType)
    console.log('Product type deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting product type:', error)
  }
}

const handleEdit = (productType) => {
  editItem.value = productType
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
