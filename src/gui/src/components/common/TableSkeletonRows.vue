<script setup lang="ts">
    type SkeletonCell = { type?: 'text' | 'chip' | 'button' | 'actions'; width?: number }
    withDefaults(
        defineProps<{
            columns: { key: string; align?: 'start' | 'center' | 'end' }[]
            cells: Record<string, SkeletonCell>
            actionCount?: number
        }>(),
        { actionCount: 2 }
    )
</script>

<template>
    <tr
        v-for="row in 5"
        :key="row"
        class="table-skeleton-row"
        aria-hidden="true"
    >
        <td
            v-for="column in columns"
            :key="column.key"
            class="v-data-table__td"
            :class="`v-data-table-column--align-${column.align || 'start'}`"
        >
            <v-skeleton-loader
                class="table-skeleton-row__cell"
                :class="{ 'table-skeleton-row__cell--actions': cells[column.key]?.type === 'actions' }"
                :type="cells[column.key]?.type || 'text'"
                :types="{ actions: `button@${actionCount}` }"
                :style="{ width: `${cells[column.key]?.width || 120}px`, maxWidth: '100%' }"
            />
        </td>
    </tr>
</template>

<style scoped>
    .table-skeleton-row__cell {
        background: transparent;
        margin-inline-end: auto;
    }

    .v-data-table-column--align-end .table-skeleton-row__cell {
        margin-inline-start: auto;
        margin-inline-end: 0;
    }

    .table-skeleton-row__cell :deep(.v-skeleton-loader__text) {
        height: 12px;
        margin: 0;
        width: 100%;
    }
    .table-skeleton-row__cell :deep(.v-skeleton-loader__chip) {
        flex: 1 1 100%;
        height: 24px;
        margin: 0;
        max-width: none;
    }

    .table-skeleton-row__cell :deep(.v-skeleton-loader__button) {
        flex: 0 0 18px;
        width: 18px;
        height: 18px;
        margin: 0;
    }

    .table-skeleton-row__cell--actions :deep(.v-skeleton-loader__actions) {
        flex-wrap: nowrap;
        justify-content: flex-end;
        gap: 12px;
    }
</style>
