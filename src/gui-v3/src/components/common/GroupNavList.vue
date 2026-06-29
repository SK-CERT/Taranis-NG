<template>
    <v-list density="compact">
        <v-list-subheader>{{ $t('assess.groups') }}</v-list-subheader>
        <v-list-item
            v-for="group in groups"
            :key="group.id"
            :active="String(group.id) === String(activeId)"
            class="pa-2"
            @click="emit('select', group)"
        >
            <div class="d-flex flex-column align-center text-center">
                <v-icon
                    :color="group.color || undefined"
                    class="mb-2"
                >
                    {{ group.icon }}
                </v-icon>
                <span class="text-body-small">
                    {{ group.translate ? $t(group.title) : group.title }}
                </span>
            </div>
        </v-list-item>
    </v-list>
</template>

<script setup lang="ts">
    /**
     * Shared OSINT-source-group sidebar list used by the Assess navigation rail
     * (AssessNav) and the attach-news-items selector (NewsItemSelector).
     *
     * Purely presentational: it renders the groups (icon on top, centered label)
     * and emits `select` with the clicked group. The parent decides what selecting
     * means — route navigation in AssessNav, group switching in the selector — and
     * controls highlighting via `activeId`.
     */
    type GroupNavItem = {
        id: string | number
        icon?: string
        color?: string | null
        title: string
        translate?: boolean | string
        route?: string
    }

    defineProps<{
        groups: GroupNavItem[]
        activeId?: string | number | null
    }>()

    const emit = defineEmits<{
        (e: 'select', group: GroupNavItem): void
    }>()
</script>
