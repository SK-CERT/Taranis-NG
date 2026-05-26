<template>
    <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
        <template #content>
            <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
                <!-- Read-only or remote -->
                <span v-if="readOnly || value.remote" class="time-value">
                    <span v-if="values.length > 1" class="time-number text--disabled">{{ index + 1 }}.</span>
                    {{ value.value || '–' }}
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
                        <v-text-field
                            v-model="value.value"
                            density="compact"
                            variant="outlined"
                            type="time"
                            :label="$t('attribute.value')"
                            :class="getLockedStyle(index)"
                            :disabled="value.locked || !canModify"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @keyup="onKeyUp(index)"
                        />
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { useAttributes } from './useAttributes'

    type AttributeValueItem = {
        index?: string | number
        value: string | null
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
</script>

<style scoped>
    .time-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .time-value {
        display: flex;
        align-items: center;
        width: 100%;
        padding: 8px 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 4px;
    }
</style>
