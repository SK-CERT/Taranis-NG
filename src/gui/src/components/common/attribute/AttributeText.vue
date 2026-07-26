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
                :class="{ 'drag-over': dragOverIndex === index, 'dragging': dragIndex === index }"
                @dragover="onDragOver(index, $event)"
                @drop="onDrop(index)"
                @dragleave="onDragLeave(index)"
            >
                <!-- Read-only or remote -->
                <span
                    v-if="readOnly || value.remote"
                    class="numbered-text-value"
                >
                    <span
                        v-if="values.length > 1"
                        class="text-number text--disabled"
                        >{{ index + 1 }}.</span
                    >
                    <span class="text-content">{{ value.value }}</span>
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
                        <div
                            v-if="values.length > 1"
                            class="reorder-controls d-flex align-center"
                        >
                            <v-icon
                                class="drag-handle"
                                size="small"
                                draggable="true"
                                :title="$t('report_item.tooltip.drag_to_reorder')"
                                :icon="ICONS.DRAG_HANDLE"
                                @dragstart="onDragStart(index, $event)"
                                @dragend="onDragEnd"
                            />
                            <span class="text-number text--disabled">{{ index + 1 }}.</span>
                            <div class="reorder-arrows d-flex flex-column ms-1">
                                <v-btn
                                    variant="text"
                                    density="compact"
                                    size="x-small"
                                    :icon="ICONS.ARROW_UP"
                                    :disabled="index === 0 || value.locked === true"
                                    :title="$t('report_item.tooltip.move_up')"
                                    @click="moveUp(index)"
                                />
                                <v-btn
                                    variant="text"
                                    density="compact"
                                    size="x-small"
                                    :icon="ICONS.ARROW_DOWN"
                                    :disabled="index === values.length - 1 || value.locked === true"
                                    :title="$t('report_item.tooltip.move_down')"
                                    @click="moveDown(index)"
                                />
                            </div>
                        </div>
                    </template>
                    <template #col_middle="{ delVisible, onDelete }">
                        <v-textarea
                            v-model="value.value"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            :label="$t('attribute.value')"
                            rows="3"
                            auto-grow
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
                        </v-textarea>
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import AttributeFieldDeleteButton from '@/components/common/buttons/AttributeFieldDeleteButton.vue'
    import { ICONS } from '@/config/ui-constants'
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

    const { canModify, addInitialValues, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp, move, moveUp, moveDown } =
        useAttributes(props)

    // Drag-and-drop reordering state.
    const dragIndex = ref<number | null>(null)
    const dragOverIndex = ref<number | null>(null)

    const onDragStart = (index: number, event: DragEvent) => {
        dragIndex.value = index
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move'
            // Some browsers require data to be set for the drag to initiate.
            event.dataTransfer.setData('text/plain', String(index))
        }
    }

    const onDragOver = (index: number, event: DragEvent) => {
        if (dragIndex.value === null) {
            return
        }
        event.preventDefault()
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move'
        }
        dragOverIndex.value = index
    }

    const onDragLeave = (index: number) => {
        if (dragOverIndex.value === index) {
            dragOverIndex.value = null
        }
    }

    const onDrop = (index: number) => {
        if (dragIndex.value !== null && dragIndex.value !== index) {
            move(dragIndex.value, index)
        }
        dragIndex.value = null
        dragOverIndex.value = null
    }

    const onDragEnd = () => {
        dragIndex.value = null
        dragOverIndex.value = null
    }

    onMounted(addInitialValues)
</script>

<style scoped>
    .text-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .numbered-text-value {
        display: flex;
        align-items: flex-start;
        width: 100%;
        padding: 8px 0;
    }

    .text-content {
        flex: 1;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
        border-top: 2px solid transparent;
    }

    .value-holder.drag-over {
        border-top-color: rgb(var(--v-theme-primary));
    }

    .value-holder.dragging {
        opacity: 0.5;
    }

    .drag-handle {
        cursor: grab;
    }

    .drag-handle:active {
        cursor: grabbing;
    }
</style>
