<template>
    <v-container
        fluid
        class="config-list-toolbar pa-2"
    >
        <!-- Search and Counts -->
        <v-row
            class="mb-2"
            align="center"
        >
            <v-col
                cols="12"
                md="9"
            >
                <div style="display: flex; align-items: center; gap: 16px; flex-wrap: nowrap">
                    <slot name="prepend" />
                    <SearchField
                        v-model="filter.search"
                        clearable
                        style="flex: 0 1 auto; min-width: 250px"
                        @update:model-value="debounceSearch"
                    />
                    <i18n-t
                        scope="global"
                        :keypath="totalCountTitle"
                        :plural="totalCount"
                        tag="div"
                        class="toolbar-filter__metric"
                    >
                        <template #count>
                            <strong>{{ n(totalCount) }}</strong>
                        </template>
                    </i18n-t>
                    <i18n-t
                        v-if="showSelectedCount"
                        scope="global"
                        :keypath="selectedCountTitle"
                        :plural="selectedCount"
                        tag="div"
                        class="toolbar-filter__metric toolbar-filter__metric--selected"
                    >
                        <template #count>
                            <strong>{{ n(selectedCount) }}</strong>
                        </template>
                    </i18n-t>
                </div>
            </v-col>
            <v-col
                cols="12"
                md="3"
                class="text-end"
            >
                <slot name="addbutton" />
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import SearchField from '@/components/common/SearchField.vue'

    type FilterState = {
        search: string
    }

    const props = defineProps({
        totalCountTitle: {
            type: String,
            default: 'toolbar_filter.total_count'
        },
        totalCount: {
            type: Number,
            default: 0
        },
        showSelectedCount: {
            type: Boolean,
            default: false
        },
        selectedCountTitle: {
            type: String,
            default: 'toolbar_filter.selected_count'
        },
        selectedCount: {
            type: Number,
            default: 0
        }
    })

    const emit = defineEmits(['update-filter'])

    const { n } = useI18n()

    // Filter state
    const filter = ref<FilterState>({
        search: ''
    })

    // Debounce search
    let searchTimeout: ReturnType<typeof setTimeout> | null = null
    const debounceSearch = (): void => {
        if (searchTimeout) clearTimeout(searchTimeout)
        searchTimeout = setTimeout(() => {
            emit('update-filter', { ...filter.value })
        }, 800)
    }

    defineExpose({
        filter
    })
</script>

<style scoped>
    .config-list-toolbar {
        width: auto;
        background: rgb(var(--v-theme-surface));
    }

    .config-list-toolbar :deep(.v-row) {
        margin: 0;
    }

    .config-list-toolbar :deep(.v-col) {
        padding: 0.25rem;
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
</style>
