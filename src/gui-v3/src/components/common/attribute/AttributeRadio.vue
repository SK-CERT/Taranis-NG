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
                    class="radio-value"
                >
                    {{ value.value }}
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
                        <v-radio-group
                            v-model="value.value"
                            inline
                            density="compact"
                            class="radio-single-row"
                            :disabled="value.locked || !canModify"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @update:model-value="onEdit(index)"
                        >
                            <v-radio
                                v-for="(option, optionIndex) in radioOptions"
                                :key="`${index}-${optionIndex}`"
                                :label="getOptionLabel(option)"
                                :value="getOptionValue(option)"
                            />
                        </v-radio-group>
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

    type RadioOptionObject = {
        value?: string | number
        title?: string
        name?: string
        id?: string | number
        [key: string]: unknown
    }

    type RadioOption = string | number | RadioOptionObject

    type AttributeGroup = {
        min_occurrence?: number
        attribute?: {
            attribute_enums?: RadioOption[]
            enum_items?: RadioOption[]
            enum_values?: RadioOption[]
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

    const radioOptions = computed<RadioOption[]>(() => {
        return (
            props.attributeGroup?.attribute?.attribute_enums ||
            props.attributeGroup?.attribute?.enum_items ||
            props.attributeGroup?.attribute?.enum_values ||
            []
        )
    })

    const getOptionLabel = (option: RadioOption): string => {
        if (option && typeof option === 'object') {
            return String(option.value ?? option.title ?? option.name ?? option.id ?? '')
        }
        return String(option ?? '')
    }

    const getOptionValue = (option: RadioOption): any => {
        if (option && typeof option === 'object') {
            return option.value ?? option.id ?? option.title ?? option.name
        }
        return option
    }

    onMounted(addInitialValues)
</script>

<style scoped>
    .radio-value {
        display: flex;
        align-items: center;
        padding: 8px 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }

    .radio-single-row :deep(.v-selection-control-group) {
        flex-wrap: nowrap;
        gap: 12px;
    }
</style>
