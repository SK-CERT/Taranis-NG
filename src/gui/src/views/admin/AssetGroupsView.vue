<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="store.assetGroups.total_count"
            total-count-title="asset_group.total_count"
            @update-filter="setFilter"
        >
            <template #addbutton><AddNewButton @click="openCreate" /></template>
        </ToolbarFilter>
        <ContentData
            :items="store.assetGroups.items"
            card-item="CardCompact"
            delete-permission="MY_ASSETS_CONFIG"
            :loading="loading"
            @edit="openEdit"
            @delete="remove"
            @refresh="load"
        />
        <AssetGroupDialog
            v-model="dialog"
            :group="selected"
            @saved="load"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { onMounted, ref } from 'vue'
    import { useAssetsStore } from '@/stores/assets'
    import { deleteAssetGroup } from '@/api/assets'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import AssetGroupDialog from '@/components/config/assets/AssetGroupDialog.vue'
    import type { AssetGroup } from '@/types/assets'
    const store = useAssetsStore()
    const loading = ref(false)
    const filter = ref({ search: '' })
    const dialog = ref(false)
    const selected = ref<AssetGroup | null>(null)
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }
    const load = async (): Promise<void> => {
        loading.value = true
        try {
            await store.loadAssetGroups(filter.value)
        } catch {
            notify('error', 'asset_group.load_error')
        } finally {
            loading.value = false
        }
    }
    const setFilter = (value: { search: string }): void => {
        filter.value = value
        load()
    }
    const openCreate = (): void => {
        selected.value = null
        dialog.value = true
    }
    const openEdit = (value: unknown): void => {
        selected.value = value as AssetGroup
        dialog.value = true
    }
    const remove = async (value: unknown): Promise<void> => {
        try {
            await deleteAssetGroup(value as AssetGroup)
            notify('success', 'asset_group.removed')
            await load()
        } catch {
            notify('error', 'asset_group.removed_error')
        }
    }
    onMounted(load)
</script>
