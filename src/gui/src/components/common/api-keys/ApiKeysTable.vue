<template>
    <v-data-table
        :headers="headers"
        :items="items"
        :aria-busy="loading"
        :items-per-page="-1"
        :row-props="rowProps"
        hide-default-footer
        item-value="id"
        class="api-keys-table"
        data-test="api-keys-table"
    >
        <template
            v-if="loading"
            #body
        >
            <TableSkeletonRows
                :columns="headers"
                :cells="skeletonCells"
                :action-count="3"
            />
        </template>

        <template #no-data>
            <div class="api-keys-table__empty">
                <v-icon size="32">mdi-key-chain-variant</v-icon>
                <span>{{ t('api_keys.no_keys') }}</span>
            </div>
        </template>

        <template #item.name="{ item }">
            <div class="py-2">
                <strong>
                    <bdi dir="auto">{{ asKey(item).name }}</bdi>
                </strong>
                <div
                    v-if="asKey(item).description"
                    class="text-caption text-medium-emphasis api-keys-table__description"
                >
                    <bdi dir="auto">{{ asKey(item).description }}</bdi>
                </div>
            </div>
        </template>

        <template #item.owner="{ item }">
            <span
                v-if="asKey(item).user"
                :title="asKey(item).user?.name || ''"
            >
                <bdi dir="auto">{{ asKey(item).user?.username }}</bdi>
            </span>
        </template>

        <template #item.key_prefix="{ item }">
            <code
                class="api-keys-table__prefix"
                dir="ltr"
                >{{ asKey(item).key_prefix }}…</code
            >
        </template>

        <template #item.scope="{ item }">
            <v-chip
                size="small"
                variant="tonal"
                :color="asKey(item).restricted ? 'primary' : undefined"
                :title="scopeTitle(asKey(item))"
                data-test="api-key-scope"
            >
                {{
                    asKey(item).restricted
                        ? t('api_keys.scope_limited_chip', { count: asKey(item).permissions.length })
                        : t('api_keys.scope_all_chip')
                }}
            </v-chip>
        </template>

        <template #item.allowed_ips="{ item }">
            <v-chip
                size="small"
                variant="tonal"
                :color="asKey(item).allowed_ips.length ? 'primary' : undefined"
                :title="asKey(item).allowed_ips.join('\n')"
                data-test="api-key-ips"
            >
                {{
                    asKey(item).allowed_ips.length
                        ? t('api_keys.ips_limited_chip', { count: asKey(item).allowed_ips.length })
                        : t('api_keys.ips_any_chip')
                }}
            </v-chip>
        </template>

        <template #item.created_at="{ item }">
            <span
                :title="asKey(item).created_by ? t('api_keys.created_by', { user: asKey(item).created_by }) : ''"
                class="text-no-wrap"
            >
                {{ formatWhen(asKey(item).created_at) }}
            </span>
        </template>

        <template #item.expires_at="{ item }">
            <v-chip
                v-if="statusOf(asKey(item)) === 'expired'"
                size="small"
                color="error"
                variant="tonal"
                prepend-icon="mdi-clock-alert-outline"
                :title="formatWhen(asKey(item).expires_at)"
                data-test="api-key-expired"
            >
                {{ t('api_keys.expired') }}
            </v-chip>
            <v-chip
                v-else-if="soon(asKey(item))"
                size="small"
                color="warning"
                variant="tonal"
                prepend-icon="mdi-clock-outline"
                :title="t('api_keys.expires_soon')"
                data-test="api-key-expires-soon"
            >
                {{ formatWhen(asKey(item).expires_at) }}
            </v-chip>
            <span
                v-else-if="asKey(item).expires_at"
                class="text-no-wrap"
                :title="formatFull(asKey(item).expires_at)"
            >
                {{ formatWhen(asKey(item).expires_at) }}
            </span>
            <span
                v-else
                class="text-medium-emphasis"
                >{{ t('api_keys.never') }}</span
            >
        </template>

        <template #item.last_used_at="{ item }">
            <span
                v-if="asKey(item).last_used_at"
                class="text-no-wrap"
                :title="lastUsedTitle(asKey(item))"
            >
                {{ formatWhen(asKey(item).last_used_at) }}
            </span>
            <span
                v-else
                class="text-medium-emphasis"
                >{{ t('api_keys.never_used') }}</span
            >
        </template>

        <template #item.actions="{ item }">
            <div class="d-flex justify-end text-no-wrap">
                <ActionButton
                    v-if="canUpdate && asKey(item).enabled"
                    icon="mdi-pause-circle-outline"
                    color="warning"
                    :title="t('api_keys.disable')"
                    class="me-1"
                    :disabled="busyId === asKey(item).id"
                    data-test="api-key-disable"
                    @click="emit('toggle', asKey(item))"
                />
                <ActionButton
                    v-else-if="canUpdate"
                    icon="mdi-play-circle-outline"
                    color="success"
                    :title="t('api_keys.enable')"
                    class="me-1"
                    :disabled="busyId === asKey(item).id"
                    data-test="api-key-enable"
                    @click="emit('toggle', asKey(item))"
                />
                <ActionButton
                    v-if="canUpdate"
                    action="edit"
                    :title="t('common.edit')"
                    class="me-1"
                    data-test="api-key-edit"
                    @click="emit('edit', asKey(item))"
                />
                <ActionButton
                    v-if="canDelete"
                    action="delete"
                    :title="t('common.delete')"
                    data-test="api-key-delete"
                    @click="emit('delete', asKey(item))"
                />
            </div>
        </template>
    </v-data-table>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import TableSkeletonRows from '@/components/common/TableSkeletonRows.vue'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { apiKeyStatus, expiresSoon, type ApiKeyItem } from './apiKeys'

    const props = withDefaults(
        defineProps<{
            items: ApiKeyItem[]
            loading?: boolean
            showOwner?: boolean
            /** Narrow layout (User settings): no Created column, dates without the time. */
            compact?: boolean
            /** The key whose enable/disable is saving: its switch waits instead of taking a second click. */
            busyId?: string | number | null
            canUpdate?: boolean
            canDelete?: boolean
        }>(),
        {
            loading: false,
            showOwner: false,
            compact: false,
            busyId: null,
            canUpdate: true,
            canDelete: true
        }
    )

    const emit = defineEmits<{
        (e: 'edit', item: ApiKeyItem): void
        (e: 'toggle', item: ApiKeyItem): void
        (e: 'delete', item: ApiKeyItem): void
    }>()

    const { t } = useI18n()
    const { formatDate, formatDateTime } = useLocaleFormatters()

    const headers = computed(() => [
        { title: t('api_keys.name'), key: 'name' },
        ...(props.showOwner ? [{ title: t('api_keys.owner'), key: 'owner', value: (item: ApiKeyItem) => item.user?.username || '' }] : []),
        { title: t('api_keys.key'), key: 'key_prefix', sortable: false },
        { title: t('api_keys.scope'), key: 'scope', sortable: false },
        { title: t('api_keys.allowed_ips'), key: 'allowed_ips', sortable: false },
        ...(props.compact ? [] : [{ title: t('api_keys.created'), key: 'created_at' }]),
        { title: t('api_keys.expires'), key: 'expires_at' },
        { title: t('api_keys.last_used'), key: 'last_used_at' },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' as const }
    ])

    type SkeletonCell = { type?: 'text' | 'chip' | 'button' | 'actions'; width?: number }
    const skeletonCells: Record<string, SkeletonCell> = {
        name: { width: 140 },
        owner: { width: 80 },
        key_prefix: { width: 110 },
        scope: { type: 'chip', width: 64 },
        allowed_ips: { type: 'chip', width: 64 },
        created_at: { width: 120 },
        expires_at: { width: 120 },
        last_used_at: { width: 120 },
        actions: { type: 'actions', width: 110 }
    }

    const asKey = (item: unknown): ApiKeyItem => item as ApiKeyItem
    const statusOf = (item: ApiKeyItem) => apiKeyStatus(item)
    const soon = (item: ApiKeyItem): boolean => expiresSoon(item)
    const formatFull = (value: string | null): string => (value ? formatDateTime(value) || value : '')
    const formatWhen = (value: string | null): string => (value && props.compact ? formatDate(value) || value : formatFull(value))
    const lastUsedTitle = (item: ApiKeyItem): string =>
        [props.compact ? formatFull(item.last_used_at) : '', item.last_used_ip ? t('api_keys.last_used_from', { ip: item.last_used_ip }) : '']
            .filter(Boolean)
            .join('\n')

    const scopeTitle = (item: ApiKeyItem): string =>
        item.restricted ? item.permissions.map((permission) => permission.name || permission.id).join('\n') : t('api_keys.scope_all')

    // Disabled and expired keys are dimmed like disabled users: readable on hover, still actionable.
    const rowProps = ({ item }: { item: unknown }): Record<string, unknown> => ({
        'class': statusOf(asKey(item)) === 'active' ? '' : 'api-key-inactive',
        'data-test': 'api-key-row'
    })
</script>

<style scoped>
    .api-keys-table__prefix {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.85em;
        white-space: nowrap;
    }

    .api-keys-table__description {
        max-width: 28ch;
        overflow-wrap: anywhere;
    }

    .api-keys-table__empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        padding: 1.5rem 0;
        color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    }

    :deep(.api-key-inactive) {
        opacity: 0.55;
    }

    :deep(.api-key-inactive:hover) {
        opacity: 1;
    }
</style>
