<template>
    <v-container
        fluid
        class="pa-4"
    >
        <CardCompact
            v-for="item in items"
            :key="item.id"
            :card="item"
            delete-permission="CONFIG_OSINT_SOURCE_DELETE"
            :multi-select-active="selectionEnabled"
            :preselected="selectedIds.includes(item.id)"
            @delete="emit('delete', item)"
            @edit="emit('edit', item)"
            @selection-change="emit('selection-change', item.id, $event)"
        />

        <v-row
            v-if="items.length === 0 && !loading"
            justify="center"
            class="mt-8"
        >
            <v-col class="text-center">
                <v-icon
                    size="64"
                    color="grey-lighten-1"
                >
                    mdi-database-off
                </v-icon>
                <p class="text-h6 text-grey-lighten-1 mt-4">{{ t('common.no_data') }}</p>
            </v-col>
        </v-row>

        <v-row
            v-if="loading"
            justify="center"
            class="mt-4"
        >
            <v-progress-circular
                indeterminate
                color="primary"
            />
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import CardCompact from '@/components/common/CardCompact.vue'

    type OSINTSourceItem = {
        id: string | number
        [key: string]: unknown
    }

    defineProps<{
        items: OSINTSourceItem[]
        loading: boolean
        selectionEnabled: boolean
        selectedIds: Array<string | number>
    }>()

    const emit = defineEmits<{
        (event: 'delete', item: OSINTSourceItem): void
        (event: 'edit', item: OSINTSourceItem): void
        (event: 'selection-change', id: string | number, selected: boolean): void
    }>()

    const { t } = useI18n()
</script>
