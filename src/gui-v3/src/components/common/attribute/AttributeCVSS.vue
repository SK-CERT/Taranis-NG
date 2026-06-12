<template>
    <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
        <template #content>
            <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="w-100 mb-1">
                <!-- Read-only or remote -->
                <div v-if="readOnly || value.remote" class="numbered-cvss-value d-flex align-center w-100 py-2">
                    <span
                        v-if="values.length > 1"
                        class="mr-2 text-disabled"
                        :style="{ userSelect: 'none', minWidth: '24px', display: 'inline-block' }"
                        >{{ index + 1 }}.</span
                    >
                    <v-chip :color="getCVSSColor(value.value)" size="small" class="mr-2">
                        {{ value.value }}
                    </v-chip>
                    <span class="text-caption text-grey">{{ getCVSSSeverity(value.value) }}</span>
                </div>

                <!-- Editable -->
                <AttributeValueLayout
                    v-if="!readOnly && canModify && !value.remote"
                    :del-button="true"
                    embed-delete
                    :occurrence="attributeGroup.min_occurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="del(index)"
                >
                    <template #col_middle="{ delVisible, onDelete }">
                        <v-text-field
                            v-model="value.value"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            label="CVSS Vector / Score"
                            :rules="[vectorRule]"
                            :class="getLockedStyle(index)"
                            :disabled="value.locked || !canModify"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @keyup="onKeyUp(index)"
                        >
                            <template #append-inner>
                                <CalculatorCVSS
                                    :model-value="value.value"
                                    :disabled="value.locked || !canModify"
                                    @update:model-value="updateFromCalculator(index, $event)"
                                />
                                <AttributeFieldDeleteButton :visible="delVisible" @delete="onDelete" />
                            </template>
                        </v-text-field>

                        <!-- Score display — always rendered at fixed height to keep layout stable -->
                        <v-row class="mb-2 ga-1">
                            <v-col v-for="scoreItem in getVectorScores(value.value) ?? placeholderScores" :key="scoreItem.name">
                                <v-sheet
                                    :color="scoreItem.color"
                                    rounded
                                    height="88"
                                    class="pa-2 text-center text-white d-flex flex-column justify-center"
                                >
                                    <div class="text-body-2 text-truncate">
                                        {{ scoreItem.label }}
                                    </div>
                                    <div class="text-body-2 font-weight-bold text-uppercase text-truncate">
                                        {{ scoreItem.severityLabel }}
                                    </div>
                                    <div class="text-subtitle-1 font-weight-medium mt-1">
                                        {{ scoreItem.score }}
                                    </div>
                                </v-sheet>
                            </v-col>
                        </v-row>
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import AttributeFieldDeleteButton from '@/components/common/buttons/AttributeFieldDeleteButton.vue'
    import CalculatorCVSS from '../CalculatorCVSS.vue'
    import { useAttributes } from './useAttributes'
    import { calculateScoreItems, detectVersion, createInstance, stripParentheses, SEVERITY_COLORS } from '../cvss-utils'
    import type { ScoreItem } from '../cvss-utils'

    const { t, te } = useI18n()

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

    const { canModify, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp } = useAttributes(props)

    // Auto-add first empty entry so the text field is always visible
    onMounted(() => {
        if (props.values?.length === 0 && canModify.value && !props.readOnly) {
            add()
        }
    })

    const NA_COLOR = SEVERITY_COLORS.na

    // Placeholder boxes use real translated labels + '–' so all three text lines
    // are always present and the box height never changes between states.
    const placeholderScores = computed<ScoreItem[]>(() => [
        {
            name: 'base',
            label: t('cvss_calculator.base_score'),
            score: '–',
            color: NA_COLOR,
            severityClass: 'severity-na',
            severityLabel: '–'
        },
        {
            name: 'temporal',
            label: t('cvss_calculator.temporal_score'),
            score: '–',
            color: NA_COLOR,
            severityClass: 'severity-na',
            severityLabel: '–'
        },
        {
            name: 'environmental',
            label: t('cvss_calculator.environmental_score'),
            score: '–',
            color: NA_COLOR,
            severityClass: 'severity-na',
            severityLabel: '–'
        }
    ])

    const vectorRule = (value: string | null | undefined): true | string => {
        if (!value || value === '') return true
        const cleaned = stripParentheses(value ?? '') ?? ''
        if (/^(10(\.0)?|[0-9](\.[0-9])?)$/.test(cleaned)) return true
        try {
            const version = detectVersion(cleaned)
            if (typeof version !== 'string' || version.length === 0) return t('cvss_calculator.validator')
            createInstance(version, cleaned)
            return true
        } catch {
            return t('cvss_calculator.validator')
        }
    }

    function updateFromCalculator(index: number, vectorValue: string): void {
        const item = props.values[index]
        if (!item) return
        item.value = vectorValue
        onKeyUp(index)
    }

    function getVectorScores(value: string | null | undefined): ScoreItem[] | null {
        return calculateScoreItems(value ?? '', t, te)
    }

    const getCVSSColor = (score: string | number | null | undefined): string => {
        const s = parseFloat(String(score ?? '0'))
        if (s >= 9.0) return 'error'
        if (s >= 7.0) return 'deep-orange'
        if (s >= 4.0) return 'warning'
        if (s > 0) return 'success'
        return 'grey'
    }

    const getCVSSSeverity = (score: string | number | null | undefined): string => {
        const s = parseFloat(String(score ?? '0'))
        if (s >= 9.0) return 'Critical'
        if (s >= 7.0) return 'High'
        if (s >= 4.0) return 'Medium'
        if (s > 0) return 'Low'
        return 'None'
    }
</script>
