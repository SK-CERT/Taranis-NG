<template>
    <section class="toolbar-filter">
        <header class="toolbar-filter__header">
            <div class="toolbar-filter__heading">
                <h1 class="toolbar-filter__title">{{ t(title) }}</h1>
            </div>

            <div class="toolbar-filter__search">
                <SearchField
                    v-model="localFilter.search"
                    :label="''"
                    variant="outlined"
                    clearable
                    @update:model-value="handleSearch"
                />
            </div>

            <div class="toolbar-filter__primary-action">
                <AddNewButton
                    v-if="showAddButton"
                    :label="addButtonLabel"
                    @click="emit('add-new')"
                />
                <slot
                    v-else
                    name="addbutton"
                />
            </div>
        </header>

        <div class="toolbar-filter__controls">
            <div
                v-if="showDayRanges"
                class="toolbar-filter__ranges"
            >
                <v-chip
                    v-for="day in typedDayRanges"
                    :key="day.value"
                    :color="localFilter.range === day.value ? 'primary' : 'default'"
                    :variant="localFilter.range === day.value ? 'tonal' : 'text'"
                    size="small"
                    :title="t(day.tooltip)"
                    @click="handleRangeChange(day.value)"
                >
                    {{ t(day.label) }}
                </v-chip>
            </div>

            <div
                v-if="showDayRanges && (hasCustomFilters || showSort)"
                class="toolbar-filter__separator"
            />

            <div class="toolbar-filter__custom">
                <slot
                    name="custom-filters"
                    :filter="localFilter"
                    :emit-filter="emitFilter"
                />
            </div>

            <div
                v-if="showSort"
                class="toolbar-filter__sort"
            >
                <slot
                    name="sort-buttons"
                    :filter="localFilter"
                    :emit-filter="emitFilter"
                    :toggle-date-sort="toggleDateSort"
                >
                    <v-chip
                        color="primary"
                        variant="flat"
                        size="small"
                        :title="dateSortTooltip"
                        @click="toggleDateSort"
                    >
                        <v-icon start>{{ ICONS.CLOCK }}</v-icon>
                        <v-icon>{{ dateSortIcon }}</v-icon>
                    </v-chip>
                </slot>
            </div>
        </div>

        <footer class="toolbar-filter__summary">
            <i18n-t
                :keypath="totalCountTitle"
                :plural="totalCount"
                tag="span"
                class="toolbar-filter__metric"
            >
                <template #count>
                    <strong>{{ n(totalCount) }}</strong>
                </template>
            </i18n-t>
            <i18n-t
                v-if="currentlyShowingCount !== undefined"
                keypath="toolbar_filter.currently_showing"
                :plural="currentlyShowingCount"
                tag="span"
                class="toolbar-filter__metric"
            >
                <template #count>
                    <strong>{{ n(currentlyShowingCount) }}</strong>
                </template>
            </i18n-t>
            <i18n-t
                v-if="showSelectedCount"
                keypath="toolbar_filter.selected_count"
                :plural="selectedCount"
                tag="span"
                class="toolbar-filter__metric toolbar-filter__metric--selected"
            >
                <template #count>
                    <strong>{{ n(selectedCount) }}</strong>
                </template>
            </i18n-t>
        </footer>
    </section>
</template>

<script setup lang="ts">
    import { ref, computed, watch, useSlots } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import SearchField from '@/components/common/SearchField.vue'

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
        totalCountTitle: {
            type: String,
            default: 'toolbar_filter.total_count'
        },
        addButtonLabel: {
            type: String,
            default: 'common.add_btn'
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

    const { t, n } = useI18n()
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
    .toolbar-filter {
        width: 100%;
    }

    .toolbar-filter__header {
        display: grid;
        grid-template-columns: minmax(12rem, 0.7fr) minmax(18rem, 1fr) auto;
        align-items: center;
        gap: clamp(0.65rem, 1.2vw, 1.2rem);
        min-height: 58px;
        padding: 0.5rem 0.8rem;
    }

    .toolbar-filter__heading {
        min-width: 0;
    }

    .toolbar-filter__title {
        overflow: hidden;
        margin: 0;
        color: rgb(var(--v-theme-on-surface));
        font-size: clamp(1.1rem, 1.6vw, 1.35rem);
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.1;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .toolbar-filter__search {
        min-width: 0;
    }

    .toolbar-filter__search :deep(.v-input__details) {
        display: none;
    }

    .toolbar-filter__search :deep(.v-field) {
        border-radius: 3px;
        background: rgba(var(--v-theme-surface-variant), 0.6);
    }

    .toolbar-filter__primary-action {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        min-width: max-content;
    }

    .toolbar-filter__controls {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        min-height: 40px;
        padding: 0.3rem 0.8rem;
        border-top: 1px solid rgba(var(--v-theme-outline), 0.22);
        background: var(--filter-controls-bg);
    }

    .toolbar-filter__ranges,
    .toolbar-filter__custom,
    .toolbar-filter__sort {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        flex-wrap: wrap;
    }

    .toolbar-filter__ranges {
        min-width: 0;
    }

    .toolbar-filter__sort {
        margin-inline-start: auto;
    }

    .toolbar-filter__separator {
        width: 1px;
        height: 24px;
        flex: 0 0 auto;
        background: rgba(var(--v-theme-outline), 0.4);
    }

    .toolbar-filter__controls :deep(.v-chip) {
        border-radius: 3px;
        font-weight: 600;
    }

    .toolbar-filter__summary {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        min-height: 28px;
        padding: 0.25rem 0.8rem;
        border-top: 1px solid rgba(var(--v-theme-outline), 0.18);
    }

    .toolbar-filter__metric {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.75rem;
    }

    .toolbar-filter__metric + .toolbar-filter__metric::before {
        width: 3px;
        height: 3px;
        margin-inline-end: 0.25rem;
        border-radius: 50%;
        background: rgba(var(--v-theme-on-surface), 0.35);
        content: '';
    }

    .toolbar-filter__metric strong {
        color: rgb(var(--v-theme-on-surface));
        font-size: 0.82rem;
    }

    .toolbar-filter__metric--selected strong {
        color: rgb(var(--v-theme-primary));
    }

    @media (max-width: 900px) {
        .toolbar-filter__header {
            grid-template-columns: 1fr auto;
        }

        .toolbar-filter__search {
            grid-column: 1 / -1;
            grid-row: 2;
        }
    }

    @media (max-width: 620px) {
        .toolbar-filter__header {
            gap: 0.5rem;
            padding: 0.5rem;
        }

        .toolbar-filter__controls {
            align-items: flex-start;
            padding: 0.3rem 0.5rem;
            overflow-x: auto;
        }

        .toolbar-filter__ranges {
            flex-wrap: nowrap;
        }

        .toolbar-filter__custom {
            flex-wrap: nowrap;
        }

        .toolbar-filter__summary {
            flex-wrap: wrap;
            padding-inline: 0.5rem;
        }
    }
</style>
