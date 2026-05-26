<template>
    <v-row justify="center" class="attribute-value-layout pt-2" @mouseenter="itemHover = true" @mouseleave="itemHover = false">
        <div class="col-left" style="position: relative">
            <slot name="col_left" />
        </div>
        <div class="col-middle">
            <slot name="col_middle" />
        </div>
        <div class="col-right">
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
        </div>
    </v-row>
</template>

<script setup lang="ts">
    import { ref, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const props = withDefaults(
        defineProps<{
            delButton?: boolean
            valIndex: number
            occurrence?: number | null | undefined
            values: Array<Record<string, unknown>>
        }>(),
        {
            delButton: false,
            occurrence: null
        }
    )

    const emit = defineEmits<{
        (e: 'del-value'): void
    }>()

    const { t } = useI18n()
    const itemHover = ref(false)

    const delButtonVisible = computed(() => {
        return itemHover.value && (props.occurrence == null || props.occurrence < props.values.length)
    })

    const handleDelete = (): void => {
        emit('del-value')
    }
</script>

<style scoped>
    .attribute-value-layout {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
    }

    .col-left {
        flex-shrink: 0;
        width: auto;
    }

    .col-middle {
        flex: 1;
        min-width: 200px;
    }

    .col-right {
        flex-shrink: 0;
        width: auto;
    }
</style>
