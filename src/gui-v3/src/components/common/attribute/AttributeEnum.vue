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
                    class="enum-value"
                >
                    <v-chip size="small">{{ value.value }}</v-chip>
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
                        <v-select
                            v-model="value.value"
                            :items="enumItems"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            :label="$t('attribute.value')"
                            :disabled="value.locked || !canModify"
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
                        </v-select>
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
    import { useAttributes } from './useAttributes'
    import { enumOptionLabel, enumOptionValue, enumOptionsOf, type EnumAttributeGroup } from './enumOptions'

    type AttributeValueItem = {
        index?: string | number
        value: string | number | null
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = EnumAttributeGroup & {
        min_occurrence?: number
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

    // The backend ships the constants as `{ id, index, value, description }` objects, so map
    // them onto the `title`/`value` pair v-select reads by default.
    const enumItems = computed(() =>
        enumOptionsOf(props.attributeGroup).map((option) => ({ title: enumOptionLabel(option), value: enumOptionValue(option) }))
    )

    onMounted(addInitialValues)
</script>

<style scoped>
    .enum-value {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }
</style>
