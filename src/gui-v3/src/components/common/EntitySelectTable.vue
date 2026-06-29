<template>
    <v-card variant="outlined" class="mt-2 mb-4">
        <v-card-title class="text-subtitle-1 bg-grey-lighten-4 d-flex align-center">
            <span>{{ title }}</span>
            <v-spacer />
            <v-text-field
                v-model="search"
                :label="t('toolbar_filter.search')"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                density="compact"
                hide-details
                single-line
                class="flex-grow-0"
                style="width: 350px"
                :disabled="disabled"
            />
            <!-- Let callers add an action (e.g. "add new") at the top-right of the table header. -->
            <div v-if="$slots['header-append']" class="ms-3">
                <slot name="header-append" />
            </div>
        </v-card-title>
        <v-data-table
            v-model="selected"
            :headers="headers"
            :items="items"
            :search="search"
            :loading="loading"
            :items-per-page="-1"
            hide-default-footer
            item-value="id"
            show-select
            density="comfortable"
            :style="disabled ? 'pointer-events: none; opacity: 0.5' : undefined"
        >
            <template #item.name="{ item }">
                <strong>{{ item.name }}</strong>
            </template>
        </v-data-table>
    </v-card>
</template>

<script setup lang="ts">
    import { ref, computed } from 'vue'
    import { useI18n } from 'vue-i18n'

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type TableHeader = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type IdSelection = Array<string | number>

    const props = withDefaults(
        defineProps<{
            modelValue: IdSelection
            title: string
            items: SelectableEntity[]
            headers: TableHeader[]
            loading?: boolean
            disabled?: boolean
        }>(),
        {
            loading: false,
            disabled: false
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: IdSelection): void
    }>()

    const { t } = useI18n()
    const search = ref('')

    const selected = computed<IdSelection>({
        get: () => props.modelValue,
        set: (value) => emit('update:modelValue', value)
    })
</script>
