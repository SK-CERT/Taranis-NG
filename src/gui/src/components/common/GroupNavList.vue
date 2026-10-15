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
                <bdi
                    dir="auto"
                    class="group-navigation__label"
                    :title="group.translate ? $t(group.title) : group.title"
                >
                    {{ group.translate ? $t(group.title) : group.title }}
                </bdi>
                <span
                    v-if="unreadCount(group) > 0"
                    class="group-navigation__count"
                    data-test="group-unread-count"
                    :title="$t('assess.unread_count', { count: formatNumber(unreadCount(group)) })"
                >
                    {{ formatCount(unreadCount(group)) }}
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
     * controls highlighting via `activeId`. `unreadCounts`, keyed by group ID, adds the
     * number of unread news items after a group's label.
     */
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { type GroupNavItem } from '@/types/routing'

    const props = withDefaults(
        defineProps<{
            groups: GroupNavItem[]
            activeId?: string | number | null
            titleKey?: string
            unreadCounts?: Record<string, number> | null
        }>(),
        { activeId: null, titleKey: 'assess.groups', unreadCounts: null }
    )

    const emit = defineEmits<{
        (e: 'select', group: GroupNavItem): void
    }>()

    const { formatNumber } = useLocaleFormatters()

    const unreadCount = (group: GroupNavItem): number => props.unreadCounts?.[String(group.id)] ?? 0

    // The rail is narrow and a group often holds thousands of unread items, so from a thousand
    // on the count is given in thousands with the SI "k" (7.6k, 12k); the tooltip keeps the
    // exact number. Not Intl's compact notation: many languages spell the unit out ("7,6 tis.").
    const formatCount = (count: number): string =>
        count < 1000 ? formatNumber(count) : `${formatNumber(count / 1000, { maximumFractionDigits: count < 10000 ? 1 : 0 })}k`
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
        flex: 1 1 auto;
        min-width: 0;
        overflow: hidden;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .group-navigation__count {
        flex: 0 0 auto;
        min-width: 1.25rem;
        margin-inline-start: -0.2rem;
        padding: 0 0.25rem;
        border-radius: 0.625rem;
        background: rgba(var(--v-theme-primary), 0.14);
        color: rgb(var(--v-theme-primary));
        font-size: 0.65rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        line-height: 1.25rem;
        text-align: center;
    }
</style>
