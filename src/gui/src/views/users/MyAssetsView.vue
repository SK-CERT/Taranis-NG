<template>
    <ViewLayout integrated-toolbar>
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
            <ContentSkeleton
                v-if="!selectedGroup && (!store.assetGroupsLoaded || store.assetGroups.items.length > 0) && !store.assetGroupsLoadError"
                variant="asset"
            />
            <ContentDataAssets
                v-else-if="selectedGroup"
                ref="content"
                @edit="openEdit"
            />
            <v-container
                v-else
                fluid
            >
                <v-alert
                    :type="store.assetGroupsLoadError ? 'error' : groupId ? 'warning' : 'info'"
                    variant="tonal"
                >
                    {{
                        $t(store.assetGroupsLoadError ? 'error.load_groups' : groupId ? 'error.not_found.message' : 'asset.no_groups_message')
                    }}
                </v-alert>
            </v-container>
        </template>
    </ViewLayout>
    <AssetDialog
        v-if="selectedGroup"
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
    import ContentSkeleton from '@/components/common/ContentSkeleton.vue'
    import ToolbarFilterAssets from '@/components/assets/ToolbarFilterAssets.vue'
    import { useAssetsStore } from '@/stores/assets'
    import type { Asset } from '@/types/assets'

    const route = useRoute()
    const store = useAssetsStore()
    const { checkPermission } = useAuth()
    const groupId = computed(() => String(route.params['groupId'] || ''))
    const selectedGroup = computed(() => store.assetGroups.items.find((group) => String(group.id) === groupId.value))
    const canCreate = computed(() => checkPermission('MY_ASSETS_CREATE') && Boolean(selectedGroup.value))
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
