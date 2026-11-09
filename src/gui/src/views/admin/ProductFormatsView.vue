<template>
    <v-container
        fluid
        class="pa-0"
    >
        <!-- Toolbar -->
        <ToolbarFilter
            :total-count="configStore.productFormats.total_count"
            total-count-title="presenters.formats.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewProductFormat
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <!-- Content -->
        <ContentData
            :items="configStore.productFormats.items"
            card-item="CardCompact"
            delete-permission="CONFIG_PRODUCT_FORMAT_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteProductFormat } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewProductFormat from '@/components/config/presenters/NewProductFormat.vue'
    import { notifyDeleteError } from '@/utils/deleteError'

    const { t } = useI18n()
    const configStore = useConfigStore()

    type FilterState = {
        search: string
    }

    type ProductFormatItem = {
        id?: string | number | null
        title?: string
        description?: string
        [key: string]: unknown
    }

    const loading = ref(false)
    const filter = ref<FilterState>({ search: '' })
    const editItem = ref<ProductFormatItem | null>(null)

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadProductFormats(filter.value)
        } catch (error) {
            console.error('Error loading product formats:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: FilterState): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (productFormat: ProductFormatItem): Promise<void> => {
        try {
            await deleteProductFormat(productFormat)
            console.log('Product format deleted successfully')
            await loadData()
        } catch (error) {
            console.error('Error deleting product format:', error)
            notifyDeleteError(error, { inUse: 'presenters.formats.removed_error' })
        }
    }

    const handleEdit = async (productFormat: ProductFormatItem): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog. The dialog
        // watches `editItem` by reference; assigning the same object again is not a
        // change, so after closing without saving a second click would do nothing.
        editItem.value = null
        await nextTick()
        editItem.value = productFormat
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(() => {
        loadData()
    })
</script>
