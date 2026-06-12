<template>
    <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
        <template #content>
            <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="w-100">
                <!-- Read-only or remote -->
                <div v-if="readOnly || value.remote" class="tlp-display d-flex align-center ga-3 py-2">
                    <v-sheet :style="getTLPStyle(value.value)" rounded class="tlp-badge px-3 py-1 text-body-2 font-weight-bold">
                        {{ value.value || '—' }}
                    </v-sheet>
                    <span class="tlp-description text-body-2 text-medium-emphasis">{{ getTLPDescription(value.value) }}</span>
                </div>

                <!-- Editable -->
                <div
                    v-if="!readOnly && canModify && !value.remote"
                    class="w-100 pt-2 pb-1"
                    @mouseenter="setHover(index, true)"
                    @mouseleave="setHover(index, false)"
                >
                    <div class="d-flex align-center ga-2">
                        <!-- Invisible phantom so both flanking elements are always the same width,
                             keeping the button group exactly centered regardless of delete visibility. -->
                        <v-btn variant="text" size="small" style="visibility: hidden; pointer-events: none" tabindex="-1">
                            <v-icon>{{ ICONS.CLOSE }}</v-icon>
                        </v-btn>

                        <!-- TLP button group - centered between the two equal-width flankers -->
                        <div style="flex: 1" class="tlp-options d-flex ga-1">
                            <button
                                v-for="tlp in tlpOptions"
                                :key="tlp"
                                class="tlp-btn tlp-button"
                                :style="getTLPButtonStyle(tlp, value.value)"
                                :disabled="value.locked || !canModify"
                                @click="setTlpValue(index, tlp)"
                            >
                                {{ tlp }}
                            </button>
                        </div>

                        <!-- Delete button - always occupies the same space; only becomes visible on hover -->
                        <v-btn
                            variant="text"
                            size="small"
                            :style="{ visibility: canShowDelete(index) ? 'visible' : 'hidden' }"
                            :title="t('report_item.tooltip.delete_value')"
                            @click="del(index)"
                        >
                            <v-icon>{{ ICONS.CLOSE }}</v-icon>
                        </v-btn>
                    </div>

                    <!-- Description centered under the button group -->
                    <div v-if="value.value" class="text-caption text-medium-emphasis text-center mt-1">
                        {{ getTLPDescription(value.value) }}
                    </div>
                </div>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { ref, onMounted, watch } from 'vue'
    import type { CSSProperties } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import { useAttributes } from './useAttributes'

    type TlpLevel = 'CLEAR' | 'GREEN' | 'AMBER' | 'AMBER+STRICT' | 'RED'

    type AttributeValueItem = {
        index?: string | number
        value: string
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = {
        min_occurrence?: number
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttributeValueItem[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number
        }>(),
        {
            readOnly: false,
            edit: false,
            modify: false
        }
    )

    const { t } = useI18n()
    const { canModify, addButtonVisible, add, del, onEdit } = useAttributes(props)

    const itemHovers = ref<Record<number, boolean>>({})

    const setHover = (index: number, state: boolean): void => {
        itemHovers.value[index] = state
    }

    const canShowDelete = (index: number): boolean => {
        return !!(
            itemHovers.value[index] &&
            (props.attributeGroup.min_occurrence == null || props.attributeGroup.min_occurrence < props.values.length)
        )
    }

    onMounted(() => {
        if (props.values?.length === 0 && canModify.value && !props.readOnly) {
            add()
        }
    })

    watch(
        () => props.values,
        (newValues: AttributeValueItem[]) => {
            newValues.forEach((val: AttributeValueItem) => {
                if (!val.value) val.value = 'CLEAR'
            })
        },
        { immediate: true, deep: true }
    )

    const tlpOptions: TlpLevel[] = ['CLEAR', 'GREEN', 'AMBER', 'AMBER+STRICT', 'RED']

    const tlpColors: Record<TlpLevel, { bg: string; text: string }> = {
        'CLEAR': { bg: '#ffffff', text: '#000000' },
        'GREEN': { bg: '#33FF00', text: '#000000' },
        'AMBER': { bg: '#FFC000', text: '#000000' },
        'AMBER+STRICT': { bg: '#FFC000', text: '#000000' },
        'RED': { bg: '#FF2B2B', text: '#ffffff' }
    }

    const tlpDescriptions: Record<TlpLevel, string> = {
        'CLEAR': 'Unrestricted - Information may be distributed without restriction',
        'GREEN': 'Community - Information may be shared within communities',
        'AMBER': 'Limited Sharing - Information should not be publicly disclosed',
        'AMBER+STRICT': 'Strictly Limited Sharing - Information should not be shared outside the organization',
        'RED': 'Not for Sharing - Information may not be shared with anyone'
    }

    const getTLPStyle = (tlp: string | null | undefined): CSSProperties => {
        const config = tlp ? tlpColors[tlp as TlpLevel] : undefined
        if (!config) return { backgroundColor: '#666666', color: '#ffffff' }
        return { backgroundColor: config.bg, color: config.text }
    }

    const getTLPButtonStyle = (tlp: TlpLevel, selectedValue: string): CSSProperties => {
        const config = tlpColors[tlp]
        const isActive = tlp === selectedValue
        // Ring contrasts with the button background. Always set boxShadow even when inactive
        // so the CSS property value changes but the property itself never appears/disappears,
        // preventing any layout recalculation that would change button size.
        const ringColor = config.text === '#ffffff' ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.75)'
        return {
            backgroundColor: config.bg,
            color: config.text,
            boxShadow: isActive ? `inset 0 0 0 3px ${ringColor}` : 'none'
        }
    }

    const getTLPDescription = (tlp: string | null | undefined): string => {
        return (tlp && tlpDescriptions[tlp as TlpLevel]) || 'Unknown TLP level'
    }

    const setTlpValue = (index: number, tlp: TlpLevel): void => {
        const item = props.values[index]
        if (!item) return
        item.value = tlp
        onEdit(index)
    }
</script>

<style scoped>
    .tlp-btn {
        height: 36px;
        /* Basis = label width, so every label always fits; extra space is shared.
           Labels are static, so widths never change after layout. */
        flex: 1 1 auto;
        white-space: nowrap;
        border: none;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        cursor: pointer;
        padding: 0 8px;
        box-sizing: border-box;
    }

    .tlp-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
