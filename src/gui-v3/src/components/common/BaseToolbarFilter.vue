<template>
    <v-container fluid class="py-0">
        <!-- Main Toolbar: Title and Search -->
        <v-toolbar flat color="surface" density="compact">
            <v-row align="center">
                <v-col cols="12" md="3">
                    <div class="text-h6">
                        {{ t(title) }}
                    </div>
                </v-col>
                <v-col cols="6" md="4">
                    <v-text-field
                        v-model="localFilter.search"
                        :prepend-inner-icon="ICONS.MAGNIFY"
                        variant="underlined"
                        density="compact"
                        hide-details
                        clearable
                        @update:model-value="handleSearch"
                    />
                </v-col>
                <v-col cols="12" md="5" style="display: flex; justify-content: flex-end; align-items: center">
                    <AddNewButton v-if="showAddButton" label="common.add_btn" @click="emit('add-new')" />
                    <slot v-else name="addbutton" />
                </v-col>
            </v-row>
        </v-toolbar>

        <v-divider />

        <!-- Filter Toolbar -->
        <v-toolbar flat color="surface" density="compact">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; width: 100%">
                <!-- Day Range Filters (optional) -->
                <div v-if="showDayRanges" style="display: flex; gap: 4px; flex-wrap: wrap">
                    <v-chip
                        v-for="day in typedDayRanges"
                        :key="day.value"
                        :color="localFilter.range === day.value ? 'primary' : 'default'"
                        :variant="localFilter.range === day.value ? 'flat' : 'outlined'"
                        size="small"
                        :title="t(day.tooltip)"
                        @click="handleRangeChange(day.value)"
                    >
                        {{ t(day.label) }}
                    </v-chip>
                </div>

                <v-divider v-if="showDayRanges && (hasCustomFilters || showSort)" vertical />

                <!-- Custom Filters Slot -->
                <slot name="custom-filters" :filter="localFilter" :emit-filter="emitFilter" />

                <div v-if="hasCustomFilters && showSort" style="flex-grow: 1" />

                <!-- Sort Buttons (optional) -->
                <div v-if="showSort" style="display: flex; gap: 4px; flex-wrap: wrap">
                    <slot name="sort-buttons" :filter="localFilter" :emit-filter="emitFilter" :toggle-date-sort="toggleDateSort">
                        <!-- Default: Single date sort toggle button -->
                        <v-chip
                            :color="localFilter.sort === 'DATE_DESC' || localFilter.sort === 'DATE_ASC' ? 'primary' : 'default'"
                            :variant="localFilter.sort === 'DATE_DESC' || localFilter.sort === 'DATE_ASC' ? 'flat' : 'outlined'"
                            size="small"
                            :title="dateSortTooltip"
                            @click="toggleDateSort"
                        >
                            <v-icon start>
                                {{ ICONS.CLOCK }}
                            </v-icon>
                            <v-icon>{{ dateSortIcon }}</v-icon>
                        </v-chip>
                    </slot>
                </div>
            </div>
        </v-toolbar>

        <v-divider />

        <!-- Count Information Toolbar (Total and Selected) -->
        <v-toolbar flat color="surface" density="compact">
            <span class="text-caption text-medium-emphasis">
                {{ $t('toolbar_filter.total_count') }}: <strong>{{ totalCount }}</strong>
                <span v-if="currentlyShowingCount !== undefined">
                    ({{ t('toolbar_filter.currently_showing') }}: <strong>{{ currentlyShowingCount }}</strong
                    >)
                </span>
                <span v-if="showSelectedCount" class="text-caption text-medium-emphasis">
                    {{ $t('toolbar_filter.selected_count') }}: <strong>{{ selectedCount }}</strong>
                </span>
            </span>
        </v-toolbar>
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, watch, useSlots } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'

    type FilterState = {
        search?: string
        range?: string
        sort?: string
        [key: string]: unknown
    }

    type DayRange = {
        value: string
        label: string
        tooltip: string
    }

    const props = defineProps({
        title: {
            type: String,
            required: true
        },
        showAddButton: {
            type: Boolean,
            default: false
        },
        totalCount: {
            type: Number,
            default: 0
        },
        currentlyShowingCount: {
            type: Number,
            default: undefined
        },
        initialFilter: {
            type: Object,
            default: () => ({
                search: '',
                range: 'ALL',
                sort: 'DATE_DESC'
            })
        },
        showDayRanges: {
            type: Boolean,
            default: true
        },
        dayRanges: {
            type: Array,
            default: () => [
                { value: 'ALL', label: 'toolbar_filter.all', tooltip: 'toolbar_filter.all' },
                { value: 'TODAY', label: 'toolbar_filter.today', tooltip: 'toolbar_filter.today' },
                { value: 'WEEK', label: 'toolbar_filter.this_week', tooltip: 'toolbar_filter.this_week' },
                { value: 'MONTH', label: 'toolbar_filter.this_month', tooltip: 'toolbar_filter.this_month' },
                {
                    value: 'LAST_7_DAYS',
                    label: 'toolbar_filter.last_7_days',
                    tooltip: 'toolbar_filter.last_7_days'
                },
                {
                    value: 'LAST_31_DAYS',
                    label: 'toolbar_filter.last_31_days',
                    tooltip: 'toolbar_filter.last_31_days'
                }
            ]
        },
        showSort: {
            type: Boolean,
            default: true
        },
        sortTooltipPrefix: {
            type: String,
            default: 'toolbar_filter'
        },
        searchDebounceMs: {
            type: Number,
            default: 300
        },
        showSelectedCount: {
            type: Boolean,
            default: false
        },
        selectedCount: {
            type: Number,
            default: 0
        }
    })

    const emit = defineEmits(['update-filter', 'add-new'])

    const { t } = useI18n()
    const slots = useSlots()

    // Local filter state
    const localFilter = ref<FilterState>({ ...(props.initialFilter as FilterState) })

    // Check if custom filters slot is used
    const hasCustomFilters = computed(() => !!slots['custom-filters'])
    const typedDayRanges = computed<DayRange[]>(() => props.dayRanges as DayRange[])

    // Date sort icon and tooltip
    const dateSortIcon = computed(() => {
        return localFilter.value.sort === 'DATE_DESC' ? ICONS.ARROW_DOWN : ICONS.ARROW_UP
    })

    const dateSortTooltip = computed(() => {
        return localFilter.value.sort === 'DATE_DESC'
            ? t(`${props.sortTooltipPrefix}.tooltip.sort.date.descending`)
            : t(`${props.sortTooltipPrefix}.tooltip.sort.date.ascending`)
    })

    // Watch for external filter updates
    watch(
        () => props.initialFilter,
        (newFilter) => {
            localFilter.value = { ...newFilter }
        },
        { deep: true }
    )

    let searchTimeout: ReturnType<typeof setTimeout> | null = null

    const handleSearch = (): void => {
        if (searchTimeout) clearTimeout(searchTimeout)
        searchTimeout = setTimeout(() => {
            emitFilter()
        }, props.searchDebounceMs)
    }

    const handleRangeChange = (range: string): void => {
        localFilter.value.range = range
        emitFilter()
    }

    const toggleDateSort = (): void => {
        localFilter.value.sort = localFilter.value.sort === 'DATE_DESC' ? 'DATE_ASC' : 'DATE_DESC'
        emitFilter()
    }

    const emitFilter = (): void => {
        emit('update-filter', { ...localFilter.value })
    }

    // Expose methods for parent components
    defineExpose({
        filter: localFilter,
        emitFilter
    })
</script>

<style scoped>
    /* Ensures horizontal scrolling for filters on small screens */
    .v-toolbar :deep(.v-toolbar__content) {
        overflow-x: auto;
    }
</style>
