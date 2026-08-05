<template>
    <v-container
        fluid
        class="config-list-toolbar"
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
                    <SearchField
                        v-model="filter.search"
                        clearable
                        style="flex: 0 1 auto; min-width: 250px"
                        @update:model-value="debounceSearch"
                    />
                    <div
                        class="text-caption text-grey"
                        style="white-space: nowrap; flex-shrink: 0"
                    >
                        {{ t(totalCountTitle) }}:
                        <strong>{{ totalCount }}</strong>
                    </div>
                    <div
                        v-if="showSelectedCount"
                        class="text-caption text-grey"
                        style="white-space: nowrap; flex-shrink: 0"
                    >
                        {{ t(selectedCountTitle) }}:
                        <strong>{{ selectedCount }}</strong>
                    </div>
                </div>
            </v-col>
            <v-col
                cols="12"
                md="3"
                class="text-right"
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

    const { t } = useI18n()

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
        margin: 0.7rem 0.7rem 0;
        padding: 0.45rem 0.6rem;
        background: rgb(var(--v-theme-surface));
    }

    .config-list-toolbar :deep(.v-row) {
        margin: 0;
    }

    .config-list-toolbar :deep(.v-col) {
        padding: 0.25rem;
    }
</style>
