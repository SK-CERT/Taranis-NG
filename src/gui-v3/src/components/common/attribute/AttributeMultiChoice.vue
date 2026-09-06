<template>
    <AttributeItemLayout
        :add-button="addButtonVisible"
        :values="values"
        @add-value="add"
    >
        <template #content>
            <div
                v-for="(value, index) in values"
                :key="`${value.index}-${index}`"
                class="value-holder"
            >
                <!-- Read-only or remote -->
                <span
                    v-if="readOnly || value.remote"
                    class="multi-choice-value"
                >
                    <v-chip
                        v-for="selected in parseSelection(value.value)"
                        :key="selected"
                        size="small"
                    >
                        {{ selected }}
                    </v-chip>
                </span>

                <!-- Editable -->
                <AttributeValueLayout
                    v-if="!readOnly && canModify && !value.remote"
                    :del-button="true"
                    :occurrence="attributeGroup.min_occurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="del(index)"
                >
                    <template #col_middle>
                        <div
                            class="multi-choice-group"
                            :class="getLockedStyle(index)"
                            @focusin="onGroupFocus(index, $event)"
                            @focusout="onGroupBlur(index, $event)"
                        >
                            <v-checkbox
                                v-for="(option, optionIndex) in choiceOptions"
                                :key="`${index}-${optionIndex}`"
                                :model-value="isChecked(value, option)"
                                :label="getOptionLabel(option)"
                                density="compact"
                                hide-details
                                :disabled="value.locked || !canModify"
                                @update:model-value="toggle(index, option, $event === true)"
                            />
                        </div>
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
    import { useAttributes } from './useAttributes'

    type AttributeValueItem = {
        index?: string | number
        value: string | number | null
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type MultiChoiceOptionObject = {
        value?: string | number
        title?: string
        name?: string
        id?: string | number
        [key: string]: unknown
    }

    type MultiChoiceOption = string | number | MultiChoiceOptionObject

    type AttributeGroup = {
        min_occurrence?: number
        attribute?: {
            attribute_enums?: MultiChoiceOption[]
            enum_items?: MultiChoiceOption[]
            enum_values?: MultiChoiceOption[]
        }
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttributeValueItem[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number | null
        }>(),
        {
            readOnly: false,
            edit: false,
            modify: false
        }
    )

    const { t } = useI18n()

    const { canModify, addInitialValues, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onEdit } = useAttributes(props)

    // Ticked values share one attribute value, newline-joined, so the whole checkbox group is a
    // single record: one lock, one version, one update per change.
    const SEPARATOR = '\n'

    const choiceOptions = computed<MultiChoiceOption[]>(() => {
        return (
            props.attributeGroup?.attribute?.attribute_enums ||
            props.attributeGroup?.attribute?.enum_items ||
            props.attributeGroup?.attribute?.enum_values ||
            []
        )
    })

    const getOptionLabel = (option: MultiChoiceOption): string => {
        if (option && typeof option === 'object') {
            return String(option.value ?? option.title ?? option.name ?? option.id ?? '')
        }
        return String(option ?? '')
    }

    const getOptionValue = (option: MultiChoiceOption): any => {
        if (option && typeof option === 'object') {
            return option.value ?? option.id ?? option.title ?? option.name
        }
        return option
    }

    const parseSelection = (raw: unknown): string[] => {
        return typeof raw === 'string' && raw.length > 0 ? raw.split(SEPARATOR).filter((entry) => entry !== '') : []
    }

    const isChecked = (value: AttributeValueItem, option: MultiChoiceOption): boolean => {
        return parseSelection(value.value).includes(String(getOptionValue(option)))
    }

    /**
     * Rewrite the whole selection on every tick. Values are stored in the order the constants are
     * declared rather than the order they were clicked, so the same selection always serializes to
     * the same string and never shows up as a spurious change to another editor.
     */
    const toggle = async (index: number, option: MultiChoiceOption, checked: boolean) => {
        const value = props.values[index]
        if (!value) {
            return
        }

        const optionValue = String(getOptionValue(option))
        const selected = new Set(parseSelection(value.value))
        if (checked) {
            selected.add(optionValue)
        } else {
            selected.delete(optionValue)
        }

        value.value = choiceOptions.value
            .map((candidate) => String(getOptionValue(candidate)))
            .filter((candidate) => selected.has(candidate))
            .join(SEPARATOR)

        await onEdit(index)
    }

    /**
     * Lock the field for the group rather than for each checkbox: tabbing across ten boxes would
     * otherwise cost ten lock/unlock round-trips. Moving focus inside the group is not a change of
     * field, so `relatedTarget` filters those out.
     */
    const movesWithinGroup = (event: FocusEvent): boolean => {
        const container = event.currentTarget as HTMLElement | null
        const target = event.relatedTarget as Node | null
        return Boolean(container && target && container.contains(target))
    }

    const onGroupFocus = (index: number, event: FocusEvent) => {
        if (!movesWithinGroup(event)) {
            onFocus(index)
        }
    }

    const onGroupBlur = (index: number, event: FocusEvent) => {
        if (!movesWithinGroup(event)) {
            onBlur(index)
        }
    }

    onMounted(addInitialValues)
</script>

<style scoped>
    .multi-choice-value {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }

    .multi-choice-group {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 16px;
        padding: 4px 0;
    }
</style>
