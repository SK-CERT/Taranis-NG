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
                    class="numbered-cwe-value"
                >
                    <span
                        v-if="values.length > 1"
                        class="cwe-number text--disabled"
                        >{{ index + 1 }}.</span
                    >
                    <a
                        :href="`https://cwe.mitre.org/data/definitions/${extractCWEId(value.value)}.html`"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        {{ value.value }}
                        <v-icon size="x-small">{{ ICONS.OPEN }}</v-icon>
                    </a>
                    <span
                        v-if="value.value_description"
                        class="cwe-description text--disabled"
                        >&nbsp;&ndash; {{ value.value_description }}</span
                    >
                </span>

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
                    <template #col_left>
                        <span
                            v-if="values.length > 1"
                            class="cwe-number text--disabled"
                            >{{ index + 1 }}.</span
                        >
                    </template>
                    <template #col_middle="{ delVisible, onDelete }">
                        <div class="cwe-fields">
                            <v-text-field
                                v-model="value.value"
                                density="compact"
                                variant="outlined"
                                hide-details="auto"
                                label="CWE"
                                class="cwe-value-field"
                                :class="getLockedStyle(index)"
                                :disabled="value.locked || !canModify"
                                @focus="onFocus(index)"
                                @blur="onBlur(index)"
                                @keyup="onKeyUp(index)"
                            />
                            <v-text-field
                                v-model="value.value_description"
                                density="compact"
                                variant="outlined"
                                hide-details="auto"
                                :label="$t('attribute.description')"
                                class="cwe-description-field"
                                :class="getLockedStyle(index)"
                                :disabled="value.locked || !canModify"
                                @focus="onFocus(index)"
                                @blur="onBlur(index)"
                                @keyup="onKeyUp(index)"
                            >
                                <template #append-inner>
                                    <AttributeFieldDeleteButton
                                        :visible="delVisible"
                                        @delete="onDelete"
                                    />
                                </template>
                            </v-text-field>
                        </div>
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
    import AttributeFieldDeleteButton from '@/components/common/buttons/AttributeFieldDeleteButton.vue'
    import { useAttributes } from './useAttributes'

    type AttributeValueItem = {
        index?: string | number
        value: string | null
        value_description?: string
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
            reportItemId: number | null
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

    const extractCWEId = (value: string | null | undefined): string => {
        const match = (value || '').match(/\d+/)
        return match ? match[0] : ''
    }
</script>

<style scoped>
    .cwe-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .numbered-cwe-value {
        display: flex;
        align-items: center;
        width: 100%;
        padding: 8px 0;
    }

    .cwe-description {
        min-width: 0;
    }

    .cwe-fields {
        display: flex;
        gap: 8px;
        width: 100%;
    }

    .cwe-value-field {
        flex: 0 0 130px;
    }

    .cwe-description-field {
        flex: 1 1 auto;
        min-width: 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }
</style>
