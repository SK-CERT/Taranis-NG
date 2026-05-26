<template>
    <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
        <template #content>
            <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
                <!-- Read-only or remote -->
                <span v-if="readOnly || value.remote" class="numbered-cve-value">
                    <span v-if="values.length > 1" class="cve-number text--disabled">{{ index + 1 }}.</span>
                    <a :href="`https://cve.mitre.org/cgi-bin/cvename.cgi?name=${value.value}`" target="_blank" rel="noopener noreferrer">
                        {{ value.value }}
                        <v-icon size="x-small">{{ ICONS.OPEN }}</v-icon>
                    </a>
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
                    <template #col_left>
                        <span v-if="values.length > 1" class="cve-number text--disabled">{{ index + 1 }}.</span>
                    </template>
                    <template #col_middle>
                        <v-text-field
                            v-model="value.value"
                            density="compact"
                            variant="outlined"
                            label="CVE-YYYY-NNNNN"
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
    import { onMounted } from 'vue'
    import { ICONS } from '@/config/ui-constants'
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

    onMounted(() => {
        if (props.values?.length === 0 && canModify.value && !props.readOnly) {
            add()
        }
    })
</script>

<style scoped>
    .cve-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .numbered-cve-value {
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
