<template>
    <v-row align="start" no-gutters class="ga-2 pt-1" @mouseenter="itemHover = true" @mouseleave="itemHover = false">
        <v-col v-if="$slots['col_left']" cols="auto">
            <slot name="col_left" />
        </v-col>
        <v-col style="min-width: 200px">
            <!-- del-visible / on-delete let an attribute embed the delete button inside its
                 input (e.g. a text field's append-inner slot) instead of the col_right column. -->
            <slot name="col_middle" :del-visible="delButtonVisible" :on-delete="handleDelete" />
        </v-col>
        <v-col v-if="!embedDelete" cols="auto">
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
    import { ref, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const props = withDefaults(
        defineProps<{
            delButton?: boolean
            embedDelete?: boolean
            valIndex: number
            occurrence?: number | null | undefined
            values: Array<Record<string, unknown>>
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
    const itemHover = ref(false)

    const delButtonVisible = computed(() => {
        // Never allow deleting the last value: the effective minimum is at least 1,
        // but a higher min_occurrence from the attribute group is still respected.
        const minRequired = Math.max(props.occurrence ?? 0, 1)
        return itemHover.value && minRequired < props.values.length
    })

    const handleDelete = (): void => {
        emit('del-value')
    }
</script>
