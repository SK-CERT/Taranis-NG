<template>
    <BaseToolbarFilter
        ref="baseFilter"
        :title="title"
        :total-count-title="totalCountTitle"
        :total-count="totalCount"
        :currently-showing-count="currentlyShowingCount"
        :initial-filter="filter"
        :show-day-ranges="true"
        :show-sort="true"
        :show-selected-count="multiSelectActive"
        :selected-count-title="'toolbar_filter.selected_count'"
        :selected-count="selectedCount"
        :show-add-button="showAddButton"
        :add-button-label="addButtonLabel"
        sort-tooltip-prefix="publish"
        :search-debounce-ms="800"
        @update-filter="handleFilterUpdate"
        @add-new="emit('add-new')"
    >
        <!-- Add Button Slot -->
        <template #addbutton>
            <slot name="addbutton" />
        </template>

        <!-- Custom Filters: Published -->
        <template #custom-filters="{ filter }">
            <div style="display: flex; gap: 4px; flex-wrap: wrap">
                <v-chip
                    size="small"
                    :color="filter['published'] === 'ALL' ? 'default' : 'primary'"
                    :variant="filter['published'] === 'ALL' ? 'outlined' : 'flat'"
                    :title="publishedFilterTooltip"
                    @click="cycleFilter('published')"
                >
                    <v-icon>{{ publishedFilterIcon }}</v-icon>
                </v-chip>
            </div>
        </template>
    </BaseToolbarFilter>

    <!-- Selection Group Toolbar -->
    <v-toolbar
        flat
        color="surface"
        density="compact"
    >
        <ToolbarGroup
            ref="toolbarGroup"
            view="publish"
            :current-filter="filter"
            @update-data="handleUpdateData"
        />

        <v-spacer />
        <v-btn
            icon
            size="small"
            :color="compactMode ? 'primary' : 'default'"
            :title="t('publish.tooltip.compact_mode')"
            @click="toggleCompactMode"
        >
            <v-icon>{{ ICONS.FORMAT_LIST_BULLETED }}</v-icon>
        </v-btn>
    </v-toolbar>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import { usePublishStore } from '@/stores/publish'
    import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'
    import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

    type PublishFilter = {
        search: string
        range: string
        published: 'ALL' | boolean
        sort: string
        compact_mode?: boolean
    }

    const props = withDefaults(
        defineProps<{
            title?: string
            totalCountTitle?: string
            showAddButton?: boolean
            addButtonLabel?: string
        }>(),
        {
            title: '',
            totalCountTitle: '',
            showAddButton: false,
            addButtonLabel: 'common.add_btn'
        }
    )

    const emit = defineEmits(['add-new'])

    const { t } = useI18n()
    const publishStore = usePublishStore()
    const baseFilter = ref<any>(null)
    const toolbarGroup = ref<any>(null)

    const currentlyShowingCount = ref(0)
    const selectedCount = ref(0)
    const filter = ref<PublishFilter>({
        search: '',
        range: 'ALL',
        published: 'ALL',
        sort: 'DATE_DESC'
    })

    const compactMode = ref(false)

    const multiSelectActive = computed(() => publishStore.getMultiSelect)

    const publishedFilterIcon = computed(() => {
        if (filter.value.published === 'ALL') return 'mdi-check-circle-outline'
        if (filter.value.published === false) return 'mdi-close-circle'
        return 'mdi-check-circle'
    })

    const publishedFilterTooltip = computed(() => {
        if (filter.value.published === 'ALL') return t('publish.tooltip.filter_all')
        if (filter.value.published === true) return t('publish.tooltip.filter_published')
        return t('publish.tooltip.filter_unpublished')
    })

    const cycleFilter = (filterType: 'published'): void => {
        if (filter.value[filterType] === 'ALL') {
            filter.value[filterType] = true
        } else if (filter.value[filterType] === true) {
            filter.value[filterType] = false
        } else {
            filter.value[filterType] = 'ALL'
        }
        emitFilter()
    }

    const totalCount = computed(() => {
        return publishStore.getProducts.total_count
    })

    const handleFilterUpdate = (updatedFilter: Partial<PublishFilter>): void => {
        filter.value = { ...filter.value, ...updatedFilter }
        emitFilter()
    }

    const toggleCompactMode = (): void => {
        compactMode.value = !compactMode.value
        emitFilter()
    }

    const emitFilter = (): void => {
        // Emit custom event for content to listen to
        window.dispatchEvent(
            new CustomEvent('update-products-filter', {
                detail: {
                    ...filter.value,
                    compact_mode: compactMode.value
                }
            })
        )
    }

    const handleUpdateData = (): void => {
        // Emit custom event for content to refresh data
        window.dispatchEvent(new CustomEvent('product-updated'))
    }

    watch(
        () => publishStore.getSelection,
        (newSelection: unknown[]) => {
            selectedCount.value = newSelection.length
        },
        { deep: true }
    )

    defineExpose({
        updateCurrentlyShowingCount: (count: number) => {
            currentlyShowingCount.value = count
        },
        updateShowingCount: (count: number) => {
            currentlyShowingCount.value = count
        },
        toolbarGroup
    })

    onMounted(() => {
        // Emit default filter on mount
        emitFilter()
    })
</script>
