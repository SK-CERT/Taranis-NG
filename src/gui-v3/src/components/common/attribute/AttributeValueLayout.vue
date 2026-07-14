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
