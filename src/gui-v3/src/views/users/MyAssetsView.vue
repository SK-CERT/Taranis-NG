<template>
    <ViewLayout>
        <template #panel>
            <ToolbarFilterAssets @update-filter="content?.updateFilter($event)">
                <template #add-button>
                    <AddNewButton
                        :show="canCreate"
                        label="asset.add"
                        @click="openCreate"
                    />
                </template>
            </ToolbarFilterAssets>
        </template>
        <template #content>
            <ContentDataAssets
                ref="content"
                @edit="openEdit"
            />
        </template>
    </ViewLayout>
    <AssetDialog
        v-model="dialog"
        :asset="selected"
        :group-id="groupId"
        @saved="content?.reload()"
    />
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useRoute } from 'vue-router'
    import { useAuth } from '@/composables/useAuth'
    import ViewLayout from '@/components/layouts/ViewLayout.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import AssetDialog from '@/components/assets/AssetDialog.vue'
    import ContentDataAssets from '@/components/assets/ContentDataAssets.vue'
    import ToolbarFilterAssets from '@/components/assets/ToolbarFilterAssets.vue'
    import type { Asset } from '@/types/assets'

    const route = useRoute()
    const { checkPermission } = useAuth()
    const groupId = computed(() => String(route.params['groupId'] || ''))
    const canCreate = computed(() => checkPermission('MY_ASSETS_CREATE') && Boolean(groupId.value))
    const content = ref<InstanceType<typeof ContentDataAssets> | null>(null)
    const dialog = ref(false)
    const selected = ref<Asset | null>(null)
    const openCreate = (): void => {
        selected.value = null
        dialog.value = true
    }
    const openEdit = (asset: Asset): void => {
        selected.value = asset
        dialog.value = true
    }
</script>
