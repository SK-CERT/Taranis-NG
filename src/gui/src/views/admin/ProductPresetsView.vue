<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="configStore.productPresets.total_count"
            total-count-title="product_presets.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewProductPreset
                    :edit-item="editItem"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <ContentData
            :items="cards"
            card-item="CardCompact"
            delete-permission="CONFIG_PRODUCT_PRESET_DELETE"
            :loading="loading"
            @delete="handleDelete"
            @edit="handleEdit"
            @refresh="loadData"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, nextTick } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteProductPreset } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import NewProductPreset from '@/components/config/product-presets/NewProductPreset.vue'
    import { notifyDeleteError } from '@/utils/deleteError'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { deliveriesToRows, OWN_LANGUAGE, type ProductPreset } from '@/types/product-presets'

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { languageName } = useContentLanguages()

    const loading = ref(false)
    const filter = ref({ search: '' })
    const editItem = ref<ProductPreset | null>(null)

    const isolate = (value: string): string => `⁨${value}⁩`

    // "Czech: Mastodon post → Mastodon CZ, Mastodon SK · JSON → SFTP · public web": what the product
    // preset sends where; a row without a language is the product's own.
    function summary(productPreset: ProductPreset): string {
        const names = new Map(
            (productPreset.deliveries || []).map((delivery) => [delivery.product_format_id, delivery.product_format_title || ''])
        )
        const channelNames = new Map(
            (productPreset.deliveries || []).map((delivery) => [
                String(delivery.publishing_channel_id),
                delivery.publishing_channel_name || ''
            ])
        )
        const parts = deliveriesToRows(productPreset.deliveries || []).map((row) => {
            const delivery = t('product.delivery', {
                format: isolate(names.get(row.product_format_id as number) || ''),
                channel:
                    row.channel_ids.length > 0
                        ? row.channel_ids.map((id) => isolate(channelNames.get(id) || id)).join(', ')
                        : t('product_presets.format_only')
            })
            return row.language === OWN_LANGUAGE
                ? delivery
                : t('product.delivery_in_language', { language: languageName(row.language), delivery })
        })
        if (productPreset.public_web_enabled) parts.push(t('product_presets.public_web'))
        return parts.join(' · ')
    }

    const cards = computed(() =>
        (configStore.productPresets.items as ProductPreset[]).map((productPreset) => ({ ...productPreset, subtitle: summary(productPreset) }))
    )

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadProductPresets(filter.value)
        } catch (error) {
            console.error('Error loading product presets:', error)
        } finally {
            loading.value = false
        }
    }

    const handleFilterUpdate = (newFilter: { search: string }): void => {
        filter.value = newFilter
        loadData()
    }

    const handleDelete = async (productPreset: ProductPreset): Promise<void> => {
        try {
            await deleteProductPreset(productPreset)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'product_presets.removed' } }))
            await loadData()
        } catch (error) {
            notifyDeleteError(error, { inUse: 'product_presets.removed_error' })
        }
    }

    const handleEdit = async (productPreset: ProductPreset): Promise<void> => {
        // Reset first so re-selecting the same row reopens the dialog (it watches by reference).
        editItem.value = null
        await nextTick()
        editItem.value = (configStore.productPresets.items as ProductPreset[]).find((item) => item.id === productPreset.id) || productPreset
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    onMounted(loadData)
</script>
