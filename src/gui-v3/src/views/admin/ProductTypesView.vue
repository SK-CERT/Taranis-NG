<template>
    <v-container fluid class="pa-0">
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.productTypes.total_count"
            total-count-title="presenters.types.total_count"
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

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteProductType } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewProductType from '@/components/config/presenters/NewProductType.vue'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type ProductTypeItem = {
        id?: string | number | null
        title?: string
        description?: string
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<ProductTypeItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadProductTypes(filter.value)
        } catch (error) {
            console.error('Error loading product types:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (productType: ProductTypeItem): Promise<void> => {
        try {
            await deleteProductType(productType)
            console.log('Product type deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting product type:', error)
        }
    }

    const handleEdit = (productType: ProductTypeItem): void => {
        editItem.value = productType
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
