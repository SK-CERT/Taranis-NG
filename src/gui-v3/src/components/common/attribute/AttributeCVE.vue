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
                    class="numbered-cve-value"
                >
                    <span
                        v-if="values.length > 1"
                        class="cve-number text--disabled"
                        >{{ index + 1 }}.</span
                    >
                    <a
                        :href="`https://cve.mitre.org/cgi-bin/cvename.cgi?name=${value.value}`"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        {{ value.value }}
                        <v-icon size="x-small">{{ ICONS.OPEN }}</v-icon>
                    </a>
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
                        <div class="attribute-lookup-column">
                            <span
                                v-if="values.length > 1"
                                class="cve-number text--disabled"
                                >{{ index + 1 }}.</span
                            >
                            <EnumSelector
                                :attribute-id="attributeGroup.attribute?.id"
                                :value-index="index"
                                :disabled="value.locked || !canModify"
                                @enum-selected="enumSelected"
                            />
                        </div>
                    </template>
                    <template #col_middle="{ delVisible, onDelete }">
                        <v-text-field
                            v-model="value.value"
                            :spellcheck="false"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            label="CVE-YYYY-NNNNN"
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
    import EnumSelector from '@/components/common/EnumSelector.vue'
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
        attribute?: {
            id?: string | number
            type?: string
            enum_values?: unknown[]
            enum_items?: unknown[]
            attribute_enums?: unknown[]
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

    const { canModify, addInitialValues, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp, enumSelected } =
        useAttributes(props)

    onMounted(addInitialValues)
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
        margin-bottom: 2px;
    }

    .attribute-lookup-column {
        display: flex;
        align-items: center;
        gap: 4px;
    }
</style>
