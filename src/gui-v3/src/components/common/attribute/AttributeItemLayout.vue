<template>
    <!-- Inner rows must be w-100: without a width, each row's flex-basis is its content's
         max-content size, so rows can end up sharing a flex line (off-center content) and the
         content width tracks text length (layout jumps when values change). -->
    <v-row justify="center" class="attribute-item-layout pt-1">
        <v-row class="w-100">
            <slot name="header">
                <v-row justify="center">
                    <!-- SORT -->
                    <v-chip-group v-if="values.length > 1" active-class="success" color="" class="pr-4">
                        <v-chip class="mr-1" :title="t('report_item.tooltip.sort_time')" @click="sort(false)">
                            <v-icon class="px-1">
                                {{ ICONS.CLOCK }}
                            </v-icon>
                        </v-chip>
                        <v-chip class="mr-1" :title="t('report_item.tooltip.sort_user')" @click="sort(true, currentUserName)">
                            <v-icon class="px-1">
                                {{ ICONS.ACCOUNT }}
                            </v-icon>
                        </v-chip>
                    </v-chip-group>
                </v-row>
            </slot>
        </v-row>
        <v-row class="ml-0 mr-4 w-100">
            <slot name="content" />
        </v-row>
        <v-row class="ml-3 mr-5 w-100">
            <slot name="footer" class="pr-0">
                <v-btn
                    v-if="addButton"
                    variant="flat"
                    size="small"
                    block
                    class="mt-1"
                    :title="t('report_item.tooltip.add_value')"
                    @click="handleAdd"
                >
                    <v-icon>{{ ICONS.PLUS }}</v-icon>
                </v-btn>
            </slot>
        </v-row>
    </v-row>
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
        }
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
        padding-left: 8px;
    }

    .attribute-item-layout :deep(.v-chip-group) {
        gap: 4px;
    }
</style>
