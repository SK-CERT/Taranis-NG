<template>
    <!-- One column: the sort chips (only with several values), the values, the add button.
         Plain flex boxes rather than v-rows: Vuetify 4 puts a 24px gap between sibling rows,
         which left most of every attribute empty. -->
    <div class="attribute-item-layout">
        <slot name="header">
            <div
                v-if="values.length > 1"
                class="attribute-item-layout__sort"
            >
                <v-chip-group
                    active-class="success"
                    color=""
                >
                    <v-chip
                        size="small"
                        :title="t('report_item.tooltip.sort_time')"
                        @click="sort(false)"
                    >
                        <v-icon>
                            {{ ICONS.CLOCK }}
                        </v-icon>
                    </v-chip>
                    <v-chip
                        size="small"
                        :title="t('report_item.tooltip.sort_user')"
                        @click="sort(true, currentUserName)"
                    >
                        <v-icon>
                            {{ ICONS.ACCOUNT }}
                        </v-icon>
                    </v-chip>
                </v-chip-group>
            </div>
        </slot>
        <div class="attribute-item-layout__values">
            <slot name="content" />
        </div>
        <slot name="footer">
            <div
                v-if="addButton"
                class="attribute-item-layout__add"
            >
                <v-btn
                    variant="text"
                    size="small"
                    color="primary"
                    :prepend-icon="ICONS.PLUS"
                    :title="t('report_item.tooltip.add_value')"
                    @click="handleAdd"
                >
                    {{ t('attribute.add_value') }}
                </v-btn>
            </div>
        </slot>
    </div>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useUserStore } from '@/stores/user'
    import { ICONS } from '@/config/ui-constants'

    type ItemValue = {
        id?: number | string
        last_updated?: unknown
        user?: {
            name?: string
        } | null
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            addButton?: boolean
            values: ItemValue[]
        }>(),
        {
            addButton: false
        }
    )

    const emit = defineEmits<{
        (e: 'add-value'): void
    }>()

    const { t } = useI18n()
    const userStore = useUserStore()
    const currentUserName = computed(() => userStore.userName || '')

    const handleAdd = (): void => {
        emit('add-value')
    }

    const sort = (sortByUser: boolean, userName?: string): void => {
        props.values.sort((a: ItemValue, b: ItemValue) => {
            if (sortByUser && userName) {
                // Current user's values first, then everyone else's.
                const aMine = a.user?.name === userName
                const bMine = b.user?.name === userName
                if (aMine !== bMine) {
                    return aMine ? -1 : 1
                }
            } else {
                // Newest first by last_updated timestamp.
                const aTime = Date.parse(String(a.last_updated ?? ''))
                const bTime = Date.parse(String(b.last_updated ?? ''))
                const aValid = !Number.isNaN(aTime)
                const bValid = !Number.isNaN(bTime)
                if (aValid && bValid && aTime !== bTime) {
                    return bTime - aTime
                }
                if (aValid !== bValid) {
                    return aValid ? -1 : 1
                }
            }
            // Stable fallback: by id.
            const aId = a.id ?? ''
            const bId = b.id ?? ''
            if (aId < bId) return -1
            if (aId > bId) return 1
            return 0
        })
    }
</script>

<style scoped>
    .attribute-item-layout {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: 100%;
    }

    /* Each value takes the whole width: a value sized to its content would make the editors
       and fields change width as their text changes. */
    .attribute-item-layout__values {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
    }

    .attribute-item-layout__values > :deep(*) {
        width: 100%;
    }

    .attribute-item-layout__sort {
        display: flex;
        justify-content: flex-end;
    }

    .attribute-item-layout__sort :deep(.v-chip-group) {
        gap: 4px;
        padding: 0;
    }

    .attribute-item-layout__add {
        display: flex;
    }
</style>
