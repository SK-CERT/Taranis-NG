<template>
    <v-row
        align="start"
        class="ga-2 pt-1"
    >
        <v-col
            v-if="$slots['col_left']"
            cols="auto"
        >
            <slot name="col_left" />
        </v-col>
        <v-col style="min-width: 200px">
            <!-- del-visible / on-delete let an attribute embed the delete button inside its
                 input (e.g. a text field's append-inner slot) instead of the col_right column. -->
            <slot
                name="col_middle"
                :del-visible="delButtonVisible"
                :on-delete="handleDelete"
            />
        </v-col>
        <v-col
            v-if="hasProvenance"
            cols="auto"
            class="attribute-provenance"
        >
            <v-menu location="bottom end">
                <template #activator="{ props: menuProps }">
                    <v-btn
                        v-bind="menuProps"
                        class="attribute-provenance__activator ms-1"
                        :icon="ICONS.CLOCK"
                        variant="text"
                        density="compact"
                        size="x-small"
                        :aria-label="provenanceLabel"
                    />
                </template>
                <v-card
                    class="attribute-provenance__details"
                    variant="outlined"
                >
                    <v-card-text class="pa-3">
                        <div
                            v-if="lastUpdated"
                            class="attribute-provenance__row"
                        >
                            <v-icon
                                :icon="ICONS.CLOCK"
                                size="small"
                            />
                            <i18n-t
                                keypath="attribute.last_updated_at"
                                tag="span"
                            >
                                <template #date>
                                    <bdi dir="auto">{{ lastUpdated }}</bdi>
                                </template>
                            </i18n-t>
                        </div>
                        <div
                            v-if="modifiedBy"
                            class="attribute-provenance__row"
                        >
                            <v-icon
                                :icon="ICONS.ACCOUNT"
                                size="small"
                            />
                            <i18n-t
                                keypath="attribute.updated_by_user"
                                tag="span"
                            >
                                <template #user>
                                    <bdi dir="auto">{{ modifiedBy }}</bdi>
                                </template>
                            </i18n-t>
                        </div>
                    </v-card-text>
                </v-card>
            </v-menu>
        </v-col>
        <v-col
            v-if="!embedDelete"
            cols="auto"
        >
            <slot name="col_right">
                <v-btn
                    v-if="delButtonVisible"
                    variant="text"
                    size="small"
                    :title="t('report_item.tooltip.delete_value')"
                    @click="handleDelete"
                >
                    <v-icon>{{ ICONS.CLOSE }}</v-icon>
                </v-btn>
            </slot>
        </v-col>
    </v-row>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'

    const props = withDefaults(
        defineProps<{
            delButton?: boolean
            embedDelete?: boolean
            valIndex: number
            occurrence?: number | null | undefined
            values: Array<{
                user?: { name?: unknown } | string | null
                last_updated?: unknown
                [key: string]: unknown
            }>
        }>(),
        {
            delButton: false,
            embedDelete: false,
            occurrence: null
        }
    )

    const emit = defineEmits<{
        (e: 'del-value'): void
    }>()

    const { t } = useI18n()
    const { formatDateTime, formatList } = useLocaleFormatters()

    const FIRST_STRONG_ISOLATE = '\u2068'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'
    const isolateAuto = (value: string): string => `${FIRST_STRONG_ISOLATE}${value}${POP_DIRECTIONAL_ISOLATE}`

    const currentValue = computed(() => props.values[props.valIndex])

    const lastUpdated = computed(() => {
        const value = currentValue.value?.last_updated
        if (typeof value !== 'string' && typeof value !== 'number') return ''
        const rawValue = String(value).trim()
        return rawValue ? formatDateTime(value) || rawValue : ''
    })

    const modifiedBy = computed(() => {
        const user = currentValue.value?.user
        const name = typeof user === 'string' ? user : user?.name
        return typeof name === 'string' || typeof name === 'number' ? String(name).trim() : ''
    })

    const hasProvenance = computed(() => Boolean(lastUpdated.value || modifiedBy.value))

    const provenanceLabel = computed(() => {
        const details: string[] = []
        if (lastUpdated.value) details.push(t('attribute.last_updated_at', { date: isolateAuto(lastUpdated.value) }))
        if (modifiedBy.value) details.push(t('attribute.updated_by_user', { user: isolateAuto(modifiedBy.value) }))
        return formatList(details, { style: 'long', type: 'conjunction' })
    })

    const delButtonVisible = computed(() => {
        // The attribute group's min_occurrence is the only floor: with a minimum of 0 even
        // the last value can be deleted, leaving the attribute empty.
        // Shown persistently (not only on hover) so it's consistent across attributes and
        // doesn't shift adjacent controls (e.g. the string open-link button) on hover.
        const minRequired = props.occurrence ?? 0
        return minRequired < props.values.length
    })

    const handleDelete = (): void => {
        emit('del-value')
    }
</script>

<style scoped>
    .attribute-provenance {
        align-self: center;
        padding-inline: 0;
    }

    .attribute-provenance__activator {
        color: rgb(var(--v-theme-outline));
    }

    .attribute-provenance__details {
        min-width: 14rem;
        max-width: min(24rem, calc(100vw - 2rem));
        background: rgb(var(--v-theme-surface));
    }

    .attribute-provenance__row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .attribute-provenance__row + .attribute-provenance__row {
        margin-top: 0.5rem;
    }
</style>
