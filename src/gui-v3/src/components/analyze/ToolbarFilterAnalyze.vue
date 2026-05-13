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
        sort-tooltip-prefix="analyze"
        @update-filter="handleFilterUpdate"
        @add-new="emit('add-new')"
    >
        <!-- Add Button Slot -->
        <template #addbutton>
            <slot name="addbutton" />
        </template>

        <!-- Custom Filters: Completed -->
        <template #custom-filters="{ filter }">
            <v-divider vertical />

            <div style="display: flex; gap: 4px; flex-wrap: wrap">
                <v-chip
                    size="small"
                    :color="filter.completed === 'ALL' ? 'default' : 'primary'"
                    :variant="filter.completed === 'ALL' ? 'outlined' : 'flat'"
                    @click="cycleFilter('completed')"
                >
                    <v-tooltip activator="parent" location="bottom">{{ completedFilterTooltip }}</v-tooltip>
                    <v-icon>{{ completedFilterIcon }}</v-icon>
                </v-chip>
            </div>

            <div style="flex-grow: 1" />

            <v-divider vertical />
        </template>
    </BaseToolbarFilter>

    <!-- Selection Group Toolbar -->
    <v-toolbar v-if="showGroupToolbar" flat color="surface" density="compact">
        <ToolbarGroup ref="toolbarGroup" view="analyze" :current-filter="filter" @update-data="handleUpdateData" />

        <v-spacer />
        <v-btn icon size="small" :color="compactMode ? 'primary' : 'default'" @click="toggleCompactMode">
            <v-tooltip activator="parent" location="bottom">
                {{ t('analyze.tooltip.compact_mode') }}
            </v-tooltip>
            <v-icon>mdi-format-list-bulleted</v-icon>
        </v-btn>
    </v-toolbar>
</template>

<script setup>
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAnalyzeStore } from '@/stores/analyze'
    import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'
    import ToolbarGroup from '@/components/common/ToolbarGroup.vue'

    const props = defineProps({
        title: {
            type: String,
            default: 'nav_menu.report_items'
        },
        totalCountTitle: {
            type: String,
            default: 'analyze.total_count'
        },
        multiSelect: Boolean,
        showGroupToolbar: {
            type: Boolean,
            default: true
        },
        showAddButton: {
            type: Boolean,
            default: false
        },
        addButtonLabel: {
            type: String,
            default: 'common.add_btn'
        }
    })

    const emit = defineEmits(['update-filter', 'update-data', 'add-new'])

    const { t } = useI18n()
    const analyzeStore = useAnalyzeStore()
    const baseFilter = ref(null)
    const toolbarGroup = ref(null)

    const totalCount = ref(0)
    const currentlyShowingCount = ref(0)
    const selectedCount = ref(0)
    const filter = ref({
        search: '',
        range: 'ALL',
        completed: 'ALL',
        sort: 'DATE_DESC'
    })

    const compactMode = ref(false)

    const multiSelectActive = computed(() => analyzeStore.getMultiSelectReport)

    const completedFilterIcon = computed(() => {
        if (filter.value.completed === 'ALL') return 'mdi-check-circle-outline'
        if (filter.value.completed === false) return 'mdi-close-circle'
        return 'mdi-check-circle'
    })

    const completedFilterTooltip = computed(() => {
        if (filter.value.completed === 'ALL') return t('analyze.tooltip.filter_all')
        if (filter.value.completed === true) return t('analyze.tooltip.filter_completed')
        return t('analyze.tooltip.filter_incomplete')
    })

    const cycleFilter = (filterType) => {
        if (filter.value[filterType] === 'ALL') {
            filter.value[filterType] = true
        } else if (filter.value[filterType] === true) {
            filter.value[filterType] = false
        } else {
            filter.value[filterType] = 'ALL'
        }
        emitFilter()
    }

    const handleFilterUpdate = (updatedFilter) => {
        filter.value = { ...filter.value, ...updatedFilter }
        emitFilter()
    }

    const toggleCompactMode = () => {
        compactMode.value = !compactMode.value
        emitFilter()
    }

    const emitFilter = () => {
        emit('update-filter', {
            ...filter.value,
            compact_mode: compactMode.value
        })
    }

    const handleUpdateData = () => {
        emit('update-data')
    }

    watch(
        () => analyzeStore.getSelectionReport,
        (newSelection) => {
            selectedCount.value = newSelection.length
        },
        { deep: true }
    )

    defineExpose({
        updateDataCount: (count) => {
            totalCount.value = count
        },
        updateCurrentlyShowingCount: (count) => {
            currentlyShowingCount.value = count
        },
        updateShowingCount: (count) => {
            currentlyShowingCount.value = count
        },
        toolbarGroup
    })

    onMounted(() => {
        // Emit default filter on mount
        emitFilter()
    })
</script>
