<template>
    <div class="asset-content">
        <div
            v-if="loading"
            class="asset-content__state"
        >
            <v-progress-circular
                indeterminate
                color="primary"
                size="64"
            />
        </div>
        <v-alert
            v-else-if="loadError"
            class="ma-3"
            type="error"
            variant="tonal"
            >{{ t('asset.load_error') }}</v-alert
        >
        <v-alert
            v-else-if="assets.length === 0"
            class="ma-3"
            type="info"
            variant="tonal"
            >{{ t('asset.no_data') }}</v-alert
        >
        <div
            v-else
            class="asset-list"
        >
            <CardAsset
                v-for="asset in assets"
                :key="asset.id"
                :asset="asset"
                @edit="emit('edit', $event)"
                @delete="remove"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { deleteAsset } from '@/api/assets'
    import { useAssetsStore } from '@/stores/assets'
    import CardAsset from './CardAsset.vue'
    import type { Asset, AssetFilter } from '@/types/assets'
    import { useSseResync } from '@/composables/useSseResync'

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

    const reloadData = async (silent = false): Promise<void> => {
        if (!groupId.value) {
            store.clearAssets()
            return
        }
        if (!silent) {
            loading.value = true
            loadError.value = false
        }
        try {
            await store.loadAssets({ group_id: groupId.value, filter: filter.value })
        } catch {
            if (!silent) {
                loadError.value = true
                notify('error', 'asset.load_error')
            }
        } finally {
            if (!silent) loading.value = false
        }
    }

    const reload = (): Promise<void> => reloadData(false)

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
    useSseResync(() => reloadData(true))
    defineExpose({ reload, updateFilter })
</script>

<style scoped>
    .asset-content {
        min-height: 100%;
        background: var(--review-list-row);
    }

    .asset-content__state {
        display: grid;
        min-height: 12rem;
        place-items: center;
    }

    .asset-list {
        overflow: hidden;
        background: var(--review-list-row);
    }
</style>
