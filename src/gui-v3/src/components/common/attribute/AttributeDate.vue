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
                    class="date-value"
                >
                    {{ formatDate(value.value) }}
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
                    <template #col_middle="{ delVisible, onDelete }">
                        <v-text-field
                            v-model="value.value"
                            type="date"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            :label="$t('attribute.value')"
                            :disabled="value.locked || !canModify"
                            style="max-width: 240px"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @update:model-value="onEdit(index)"
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
    import { useI18n } from 'vue-i18n'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import AttributeFieldDeleteButton from '@/components/common/buttons/AttributeFieldDeleteButton.vue'
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

    onMounted(addInitialValues)

    const formatDate = (dateStr: string | null | undefined): string => {
        if (!dateStr) return ''
        try {
            return new Date(dateStr).toLocaleDateString()
        } catch {
            return dateStr
        }
    }
</script>

<style scoped>
    .date-value {
        display: flex;
        align-items: center;
        padding: 8px 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }
</style>
