<template>
    <div class="link-list">
        <!-- Read-only: a list of links -->
        <ul
            v-if="readOnly"
            class="link-list__readonly"
        >
            <li
                v-for="link in values"
                :key="rowKey(link)"
                class="link-list__readonly-row"
            >
                <a
                    v-if="isHttpUrl(link.value)"
                    :href="String(link.value).trim()"
                    target="_blank"
                    rel="noopener noreferrer"
                    ><bdi dir="ltr">{{ link.value }}</bdi></a
                >
                <bdi
                    v-else
                    dir="auto"
                    >{{ link.value }}</bdi
                >
            </li>
        </ul>

        <template v-else>
            <div
                v-for="(link, index) in values"
                :key="rowKey(link)"
                class="link-list__row"
                :class="{ 'drag-over': dragOverIndex === index, 'dragging': dragIndex === index }"
                data-test="link-row"
                @dragover="onDragOver(index, $event)"
                @drop="onDrop(index)"
                @dragleave="onDragLeave(index)"
            >
                <!-- Insert above this row: revealed while the row is hovered -->
                <div
                    v-if="canInsert"
                    class="link-list__gap"
                >
                    <v-btn
                        class="link-list__insert"
                        size="x-small"
                        variant="tonal"
                        color="primary"
                        density="comfortable"
                        :icon="ICONS.INSERT_LINK"
                        :title="t('links.insert_here')"
                        :aria-label="t('links.insert_here')"
                        data-test="link-insert"
                        @click="emit('insert', index)"
                    />
                </div>

                <AttributeValueLayout
                    :del-button="true"
                    embed-delete
                    :occurrence="minOccurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="requestRemove(index)"
                >
                    <!-- Reordering controls: only when there is something to reorder -->
                    <template
                        v-if="values.length > 1"
                        #col_left
                    >
                        <div class="link-list__controls d-flex align-center">
                            <v-icon
                                class="drag-handle"
                                size="small"
                                draggable="true"
                                :title="t('report_item.tooltip.drag_to_reorder')"
                                :icon="ICONS.DRAG_HANDLE"
                                @dragstart="onDragStart(index, $event)"
                                @dragend="onDragEnd"
                            />
                            <div class="d-flex flex-column ms-1">
                                <v-btn
                                    variant="text"
                                    density="compact"
                                    size="x-small"
                                    :icon="ICONS.ARROW_UP"
                                    :disabled="disabled || index === 0 || link.locked === true"
                                    :title="t('report_item.tooltip.move_up')"
                                    @click="emit('move', index, index - 1)"
                                />
                                <v-btn
                                    variant="text"
                                    density="compact"
                                    size="x-small"
                                    :icon="ICONS.ARROW_DOWN"
                                    :disabled="disabled || index === values.length - 1 || link.locked === true"
                                    :title="t('report_item.tooltip.move_down')"
                                    @click="emit('move', index, index + 1)"
                                />
                            </div>
                        </div>
                    </template>
                    <template #col_middle="{ delVisible, onDelete }">
                        <v-text-field
                            v-model="link.value"
                            dir="ltr"
                            :spellcheck="false"
                            density="compact"
                            variant="outlined"
                            hide-details="auto"
                            :label="t('links.url')"
                            :class="{ 'locked-style': link.locked === true }"
                            :disabled="disabled || link.locked === true"
                            @focus="emit('focus', index)"
                            @blur="emit('blur', index)"
                            @keyup="emit('keyup', index)"
                        >
                            <template #append-inner>
                                <v-chip
                                    v-if="citations(link) > 0"
                                    size="x-small"
                                    variant="tonal"
                                    color="primary"
                                    class="me-1"
                                    :title="t('links.cited_hint')"
                                    data-test="link-citations"
                                    >{{ t('links.cited', { count: citations(link) }) }}</v-chip
                                >
                                <v-btn
                                    v-if="isHttpUrl(link.value)"
                                    icon
                                    variant="text"
                                    density="compact"
                                    tabindex="-1"
                                    :href="String(link.value).trim()"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    :title="t('report_item.tooltip.open_link')"
                                    @mousedown.stop
                                    @click.stop
                                >
                                    <v-icon>{{ ICONS.OPEN }}</v-icon>
                                </v-btn>
                                <AttributeFieldDeleteButton
                                    :visible="delVisible && !disabled"
                                    @delete="onDelete"
                                />
                            </template>
                        </v-text-field>
                    </template>
                </AttributeValueLayout>
            </div>

            <div class="link-list__footer d-flex ga-2 mt-1">
                <v-btn
                    v-if="canInsert"
                    variant="flat"
                    size="small"
                    class="flex-grow-1"
                    :title="t('links.add')"
                    :aria-label="t('links.add')"
                    data-test="link-add"
                    @click="emit('insert', values.length)"
                >
                    <v-icon>{{ ICONS.PLUS }}</v-icon>
                </v-btn>
                <slot name="actions" />
            </div>
        </template>

        <ConfirmationDialog
            v-model="confirmOpen"
            title-key="links.delete_cited_title"
            :message="t('links.delete_cited_message', { count: pendingCitations })"
            @confirm="confirmRemove"
        />
    </div>
</template>

<script setup lang="ts">
    import { computed, ref, toRaw } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AttributeValueLayout from '@/components/common/attribute/AttributeValueLayout.vue'
    import AttributeFieldDeleteButton from '@/components/common/buttons/AttributeFieldDeleteButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import { ICONS } from '@/config/ui-constants'
    import { isHttpUrl, type LinkValue } from '@/utils/linkReferences'

    /**
     * An ordered list of citable links: rows that can be reordered, inserted between
     * and removed. The rows are edited in place (v-model on `value`); everything that changes
     * the list itself is left to the parent through events, because a report item persists
     * those changes value by value while a product saves its links as a whole.
     */
    const props = withDefaults(
        defineProps<{
            values: LinkValue[]
            readOnly?: boolean
            disabled?: boolean
            minOccurrence?: number
            maxOccurrence?: number | null
            /** How often the text of the form cites a link key. */
            citationCount?: (key: string) => number
        }>(),
        {
            readOnly: false,
            disabled: false,
            minOccurrence: 0,
            maxOccurrence: null,
            citationCount: () => 0
        }
    )

    const emit = defineEmits<{
        (e: 'insert', index: number): void
        (e: 'remove', index: number): void
        (e: 'move', from: number, to: number): void
        (e: 'focus', index: number): void
        (e: 'blur', index: number): void
        (e: 'keyup', index: number): void
    }>()

    const { t } = useI18n()

    const canInsert = computed(() => !props.disabled && props.values.length < (props.maxOccurrence ?? Infinity))

    const citations = (link: LinkValue): number =>
        typeof link.value_description === 'string' && link.value_description ? props.citationCount(link.value_description) : 0

    // Rows are keyed by the link object, not by its link key: those can repeat in the list (links
    // of attached remote report items, a refresh that caught the server half-way through a
    // reorder), and a repeated v-for key leaves an orphaned row behind that edits another link.
    const rowIds = new WeakMap<object, number>()
    let nextRowId = 0
    const rowKey = (link: LinkValue): number => {
        const raw = toRaw(link)
        let id = rowIds.get(raw)
        if (id === undefined) {
            id = nextRowId++
            rowIds.set(raw, id)
        }
        return id
    }

    // Removing a cited link asks first: its citations would be left out of the output.
    const confirmOpen = ref(false)
    const pendingIndex = ref<number | null>(null)
    const pendingCitations = ref(0)

    const requestRemove = (index: number): void => {
        const link = props.values[index]
        if (!link) return
        const count = citations(link)
        if (count === 0) {
            emit('remove', index)
            return
        }
        pendingIndex.value = index
        pendingCitations.value = count
        confirmOpen.value = true
    }

    const confirmRemove = (): void => {
        if (pendingIndex.value !== null) {
            emit('remove', pendingIndex.value)
        }
        pendingIndex.value = null
    }

    // Drag-and-drop reordering.
    const dragIndex = ref<number | null>(null)
    const dragOverIndex = ref<number | null>(null)

    const onDragStart = (index: number, event: DragEvent): void => {
        dragIndex.value = index
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move'
            // Some browsers require data to be set for the drag to initiate.
            event.dataTransfer.setData('text/plain', String(index))
        }
    }

    const onDragOver = (index: number, event: DragEvent): void => {
        if (dragIndex.value === null) return
        event.preventDefault()
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move'
        }
        dragOverIndex.value = index
    }

    const onDragLeave = (index: number): void => {
        if (dragOverIndex.value === index) {
            dragOverIndex.value = null
        }
    }

    const onDrop = (index: number): void => {
        if (dragIndex.value !== null && dragIndex.value !== index && !props.disabled) {
            emit('move', dragIndex.value, index)
        }
        dragIndex.value = null
        dragOverIndex.value = null
    }

    const onDragEnd = (): void => {
        dragIndex.value = null
        dragOverIndex.value = null
    }
</script>

<style scoped>
    .link-list {
        width: 100%;
    }

    .link-list__row {
        position: relative;
        border-top: 2px solid transparent;
    }

    .link-list__row.drag-over {
        border-top-color: rgb(var(--v-theme-primary));
    }

    .link-list__row.dragging {
        opacity: 0.5;
    }

    /* The insert button sits on the boundary above its row. */
    .link-list__gap {
        position: absolute;
        inset-inline-start: 50%;
        top: -10px;
        z-index: 1;
        transform: translateX(-50%);
    }

    .link-list__insert {
        opacity: 0;
        transition: opacity 0.15s ease-in-out;
    }

    .link-list__row:hover .link-list__insert,
    .link-list__insert:focus-visible {
        opacity: 1;
    }

    @media (hover: none) {
        .link-list__insert {
            opacity: 1;
        }
    }

    .link-list__readonly {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .link-list__readonly-row {
        display: flex;
        align-items: baseline;
        padding: 4px 0;
        word-break: break-all;
    }

    .link-list__readonly-row a {
        color: rgb(var(--v-theme-primary));
    }

    .drag-handle {
        cursor: grab;
    }

    .drag-handle:active {
        cursor: grabbing;
    }
</style>
