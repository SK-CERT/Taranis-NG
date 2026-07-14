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
                    class="numbered-string-value"
                >
                    <span
                        v-if="values.length > 1"
                        class="string-number text--disabled"
                        >{{ index + 1 }}.</span
                    >
                    <span class="string-content">
                        <a
                            v-if="isUrl(value.value)"
                            :href="value.value ?? undefined"
                            target="_blank"
                            rel="noopener noreferrer"
                            >{{ value.value }}</a
                        >
                        <template v-else>{{ value.value }}</template>
                    </span>
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
                            <span class="string-number text--disabled">{{ index + 1 }}.</span>
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
                        <v-text-field
                            v-model="value.value"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            :label="$t('attribute.value')"
                            :class="getLockedStyle(index)"
                            :disabled="value.locked || !canModify"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @keyup="onKeyUp(index)"
                        >
                            <template #append-inner>
                                <!-- When the value is a URL, offer to open it in a new tab. -->
                                <v-btn
                                    v-if="isUrl(value.value)"
                                    icon
                                    variant="text"
                                    density="compact"
                                    tabindex="-1"
                                    :href="value.value ?? undefined"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    :title="$t('report_item.tooltip.open_link')"
                                    @mousedown.stop
                                    @click.stop
                                >
                                    <v-icon>{{ ICONS.OPEN }}</v-icon>
                                </v-btn>
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

    // Treat a value as a link only when it is an explicit http(s) URL — avoids false positives
    // and never produces javascript:/data: links.
    const isUrl = (value: unknown): boolean => {
        if (typeof value !== 'string') {
            return false
        }
        const trimmed = value.trim()
        if (!/^https?:\/\//i.test(trimmed)) {
            return false
        }
        try {
            const url = new URL(trimmed)
            return url.protocol === 'http:' || url.protocol === 'https:'
        } catch {
            return false
        }
    }

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
    .string-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .numbered-string-value {
        display: flex;
        align-items: center;
        width: 100%;
        padding: 8px 0;
    }

    .string-content {
        flex: 1;
        word-break: break-word;
    }

    .string-content a {
        color: rgb(var(--v-theme-primary));
        word-break: break-all;
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
