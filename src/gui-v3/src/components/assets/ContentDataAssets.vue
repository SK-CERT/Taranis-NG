<template>
    <v-container fluid>
        <div
            v-if="loading"
            class="text-center pa-12"
        >
            <v-progress-circular
                indeterminate
                color="primary"
                size="64"
            />
        </div>
        <v-alert
            v-else-if="loadError"
            type="error"
            variant="tonal"
            >{{ t('asset.load_error') }}</v-alert
        >
        <v-alert
            v-else-if="assets.length === 0"
            type="info"
            variant="tonal"
            >{{ t('asset.no_data') }}</v-alert
        >
        <v-row v-else>
            <v-col
                v-for="asset in assets"
                :key="asset.id"
                cols="12"
                sm="6"
                md="4"
                lg="3"
            >
                <CardAsset
                    :asset="asset"
                    @edit="emit('edit', $event)"
                    @delete="remove"
                />
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { deleteAsset } from '@/api/assets'
    import { useAssetsStore } from '@/stores/assets'
    import CardAsset from './CardAsset.vue'
    import type { Asset, AssetFilter } from '@/types/assets'

    const emit = defineEmits<{ (e: 'edit', asset: Asset): void }>()
    const { t } = useI18n()
    const route = useRoute()
    const store = useAssetsStore()
    const loading = ref(false)
    const loadError = ref(false)
    const filter = ref<AssetFilter>({ search: '', vulnerable: false, sort: 'ALPHABETICAL' })
    const groupId = computed(() => String(route.params['groupId'] || ''))
    const assets = computed(() => store.assets.items)
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    const reload = async (): Promise<void> => {
        if (!groupId.value) {
            store.clearAssets()
            return
        }
        loading.value = true
        loadError.value = false
        try {
            await store.loadAssets({ group_id: groupId.value, filter: filter.value })
        } catch {
            loadError.value = true
            notify('error', 'asset.load_error')
        } finally {
            loading.value = false
        }
    }

    const remove = async (asset: Asset): Promise<void> => {
        try {
            await deleteAsset({ id: asset.id, asset_group_id: groupId.value })
            notify('success', 'asset.removed')
            await reload()
        } catch {
            notify('error', 'asset.removed_error')
        }
    }

    const updateFilter = (value: AssetFilter): void => {
        filter.value = { ...value }
        reload()
    }

    watch(groupId, reload)
    onMounted(reload)
    defineExpose({ reload, updateFilter })
</script>
