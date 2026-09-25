<template>
    <BaseToolbarFilter
        title="main_menu.my_assets"
        total-count-title="asset.total_count"
        :total-count="assetsStore.assets.total_count"
        :initial-filter="initialFilter"
        :show-day-ranges="false"
        :show-sort="true"
        @update-filter="handleFilterUpdate"
    >
        <template #addbutton>
            <slot name="add-button" />
        </template>

        <template #custom-filters="{ filter, emitFilter }">
            <v-chip
                size="small"
                :color="filter['vulnerable'] ? 'error' : 'default'"
                :variant="filter['vulnerable'] ? 'flat' : 'outlined'"
                :title="$t('asset.vulnerable')"
                @click="toggleVulnerable(filter, emitFilter)"
            >
                <v-icon>mdi-shield-alert</v-icon>
            </v-chip>
        </template>

        <template #sort-buttons="{ filter, emitFilter }">
            <v-chip
                size="small"
                :color="filter.sort === 'ALPHABETICAL' ? 'primary' : 'default'"
                :variant="filter.sort === 'ALPHABETICAL' ? 'flat' : 'outlined'"
                :title="$t('asset.sort.alphabetical')"
                @click="selectSort(filter, 'ALPHABETICAL', emitFilter)"
            >
                <v-icon>mdi-sort-alphabetical-ascending</v-icon>
            </v-chip>
            <v-chip
                size="small"
                :color="filter.sort === 'VULNERABILITY' ? 'primary' : 'default'"
                :variant="filter.sort === 'VULNERABILITY' ? 'flat' : 'outlined'"
                :title="$t('asset.sort.vulnerability')"
                @click="selectSort(filter, 'VULNERABILITY', emitFilter)"
            >
                <v-icon>mdi-sort-numeric-descending</v-icon>
            </v-chip>
        </template>
    </BaseToolbarFilter>
</template>

<script setup lang="ts">
    import { reactive } from 'vue'
    import { useAssetsStore } from '@/stores/assets'
    import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'

    type AssetFilter = {
        search: string
        vulnerable: boolean
        sort: 'ALPHABETICAL' | 'VULNERABILITY'
        [key: string]: unknown
    }

    type EmitFilter = () => void

    const assetsStore = useAssetsStore()
    const emit = defineEmits<{
        (e: 'update-filter', payload: AssetFilter): void
    }>()

    const initialFilter = reactive<AssetFilter>({
        search: '',
        vulnerable: false,
        sort: 'ALPHABETICAL'
    })

    const toggleVulnerable = (filter: Record<string, unknown>, emitFilter: EmitFilter): void => {
        filter['vulnerable'] = !filter['vulnerable']
        emitFilter()
    }

    const selectSort = (filter: Record<string, unknown>, sort: AssetFilter['sort'], emitFilter: EmitFilter): void => {
        filter['sort'] = sort
        emitFilter()
    }

    const handleFilterUpdate = (filter: Record<string, unknown>): void => {
        emit('update-filter', {
            search: typeof filter['search'] === 'string' ? filter['search'] : '',
            vulnerable: Boolean(filter['vulnerable']),
            sort: filter['sort'] === 'VULNERABILITY' ? 'VULNERABILITY' : 'ALPHABETICAL'
        })
    }
</script>
