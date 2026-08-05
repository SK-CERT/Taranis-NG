<template>
    <v-list
        density="compact"
        class="group-navigation"
    >
        <v-list-subheader>{{ $t(titleKey) }}</v-list-subheader>
        <v-list-item
            v-for="group in groups"
            :key="group.id"
            :active="String(group.id) === String(activeId)"
            :data-group-id="group.id"
            class="group-navigation__item"
            @click="emit('select', group)"
        >
            <div class="group-navigation__content">
                <v-icon
                    :color="group.color || undefined"
                    size="22"
                >
                    {{ group.icon }}
                </v-icon>
                <span class="group-navigation__label">
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
    import { type GroupNavItem } from '@/types/routing'

    withDefaults(
        defineProps<{
            groups: GroupNavItem[]
            activeId?: string | number | null
            titleKey?: string
        }>(),
        { activeId: null, titleKey: 'assess.groups' }
    )

    const emit = defineEmits<{
        (e: 'select', group: GroupNavItem): void
    }>()
</script>

<style scoped>
    .group-navigation__item {
        padding: 0.35rem 0.45rem !important;
    }

    .group-navigation__content {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .group-navigation__label {
        overflow: hidden;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
