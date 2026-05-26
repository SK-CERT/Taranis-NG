<template>
    <v-row justify="center" class="attribute-item-layout pt-2">
        <v-row no-gutters>
            <slot name="header">
                <v-row justify="center">
                    <!-- SORT -->
                    <v-chip-group v-if="values.length > 1" active-class="success" color="" class="pr-4">
                        <v-chip size="small" class="px-0 mr-1" :title="t('report_item.tooltip.sort_time')" @click="sort(false)">
                            <v-icon class="px-2" size="small">
                                {{ ICONS.CLOCK }}
                            </v-icon>
                        </v-chip>
                        <v-chip
                            size="small"
                            class="px-0 mr-1"
                            :title="t('report_item.tooltip.sort_user')"
                            @click="sort(true, currentUserName)"
                        >
                            <v-icon class="px-2" size="small">
                                {{ ICONS.ACCOUNT }}
                            </v-icon>
                        </v-chip>
                    </v-chip-group>
                </v-row>
            </slot>
        </v-row>
        <v-row class="ml-0 mr-4">
            <slot name="content" />
        </v-row>
        <v-row class="ml-3 mr-5">
            <slot name="footer" class="pr-0">
                <v-btn
                    v-if="addButton"
                    variant="flat"
                    size="small"
                    block
                    class="mt-2"
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
                if (userName === a.user?.name && userName !== b.user?.name) {
                    return -1
                } else if (userName !== a.user?.name && userName === b.user?.name) {
                    return 1
                }
            }
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
