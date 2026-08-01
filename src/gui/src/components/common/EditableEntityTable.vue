<template>
    <v-card
        variant="outlined"
        class="mt-2 mb-4"
    >
        <v-card-title class="text-subtitle-1 bg-grey-lighten-4 d-flex align-center">
            <span>{{ title }}</span>
            <v-spacer />
            <SearchField
                v-if="searchable"
                v-model="search"
                :width="350"
                :disabled="disabled"
                class="flex-grow-0"
            />
            <div
                v-if="!disabled"
                class="ms-3"
            >
                <AddNewButton @click="openDialog()" />
            </div>
        </v-card-title>

        <component
            :is="server ? 'v-data-table-server' : 'v-data-table'"
            v-bind="tableProps"
            density="comfortable"
            @update:options="(o: TableOptions) => emit('update:options', o)"
        >
            <!-- Forward any cell/template slots the caller defined (e.g. #item.name). -->
            <template
                v-for="name in passthroughSlots"
                #[name]="slotData"
            >
                <slot
                    :name="name"
                    v-bind="slotData"
                />
            </template>

            <template #item.actions="{ item, index }">
                <ActionButton
                    v-if="reorderable && !disabled"
                    icon="mdi-arrow-up-bold"
                    :title="t('common.up')"
                    @click="move(index, -1)"
                />
                <ActionButton
                    v-if="reorderable && !disabled"
                    icon="mdi-arrow-down-bold"
                    :title="t('common.down')"
                    @click="move(index, 1)"
                />
                <ActionButton
                    v-if="!disabled"
                    action="edit"
                    :title="t('common.edit')"
                    class="mr-1"
                    @click="openDialog(item as Row, index)"
                />
                <ActionButton
                    v-if="!disabled"
                    action="delete"
                    :title="t('common.delete')"
                    @click="remove(item as Row, index)"
                />
            </template>

            <template #no-data>
                <div class="text-center pa-4 text-grey">
                    {{ noDataText || t('common.no_data') }}
                </div>
            </template>
        </component>
    </v-card>

    <!-- Add / edit dialog -->
    <v-dialog
        v-model="dialog"
        :max-width="dialogMaxWidth"
        persistent
        scrollable
        @keydown.esc="requestClose"
    >
        <v-card>
            <DialogToolbar
                :title="editedIndex === -1 ? addTitle : editTitle"
                :saving="saving"
                :save-disabled="saveDisabled"
                @cancel="requestClose"
                @save="save"
            />
            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="save"
                >
                    <!-- Caller supplies the edit fields, bound to the working copy. -->
                    <slot
                        name="form"
                        :item="editedItem"
                        :is-new="editedIndex === -1"
                    />
                </v-form>
            </v-card-text>
        </v-card>

        <UnsavedChangesDialog
            v-model="confirmVisible"
            @continue="continueEditing"
            @save="confirmSaveAndClose"
            @discard="discardAndClose"
        />
    </v-dialog>
</template>

<script setup lang="ts" generic="Row extends Record<string, unknown>">
    import { ref, computed, useSlots, type Ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import SearchField from '@/components/common/SearchField.vue'

    type TableHeader = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
        width?: string
    }

    type TableOptions = {
        page: number
        itemsPerPage: number
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            title: string
            headers: TableHeader[]
            /** Factory for a blank row used by "Add new". */
            defaultItem: () => Row
            addTitle: string
            editTitle: string
            dialogMaxWidth?: string | number
            disabled?: boolean
            reorderable?: boolean
            searchable?: boolean
            noDataText?: string
            /** Disable the dialog's Save button (e.g. a required selection is empty). */
            saveDisabled?: boolean
            /** Spinner on the dialog Save button while the caller persists. */
            saving?: boolean
            // --- server / controlled mode ---
            server?: boolean
            items?: Row[]
            itemsLength?: number
            loading?: boolean
            itemsPerPageOptions?: number[]
        }>(),
        {
            dialogMaxWidth: 600,
            disabled: false,
            reorderable: false,
            searchable: false,
            noDataText: '',
            saveDisabled: false,
            saving: false,
            server: false,
            itemsLength: 0,
            loading: false,
            itemsPerPageOptions: () => [25, 50, 100]
        }
    )

    const emit = defineEmits<{
        (e: 'update:options', options: TableOptions): void
        // Controlled mode: caller persists the row and closes the dialog (via v-model:dialog).
        (e: 'save', item: Row, ctx: { isNew: boolean }): void
        (e: 'delete', item: Row, index: number): void
    }>()

    // In-memory list (uncontrolled mode). Ignored when `server` is set.
    const model = defineModel<Row[]>({ default: () => [] })
    // Dialog open state; callers may bind it (v-model:dialog) to close after async save.
    const dialog = defineModel<boolean>('dialog', { default: false })
    // Search text; client-filtered in uncontrolled mode, emitted for the caller in server mode.
    const search = defineModel<string>('search', { default: '' })
    const page = defineModel<number>('page', { default: 1 })
    const itemsPerPage = defineModel<number>('itemsPerPage', { default: 25 })

    const { t } = useI18n()
    const slots = useSlots()

    const formRef = ref<{ validate: () => Promise<{ valid: boolean }>; resetValidation?: () => void } | null>(null)
    const editedIndex = ref(-1)
    const editedItem = ref(props.defaultItem()) as Ref<Row>

    const rows = computed<Row[]>(() => (props.server ? (props.items ?? []) : model.value))

    // Forward every "item.*"/cell slot the caller passes, except the actions column
    // (which this component renders) and the form slot (used by the dialog).
    const passthroughSlots = computed(() =>
        Object.keys(slots).filter((name) => name !== 'item.actions' && name !== 'form' && name !== 'no-data')
    )

    const tableProps = computed(() => {
        const base: Record<string, unknown> = {
            headers: props.headers,
            items: rows.value,
            loading: props.loading
        }
        if (props.server) {
            base['itemsLength'] = props.itemsLength
            base['page'] = page.value
            base['onUpdate:page'] = (v: number) => (page.value = v)
            base['itemsPerPage'] = itemsPerPage.value
            base['onUpdate:itemsPerPage'] = (v: number) => (itemsPerPage.value = v)
            base['itemsPerPageOptions'] = props.itemsPerPageOptions
        } else {
            base['itemsPerPage'] = -1
            base['hideDefaultFooter'] = true
            if (props.searchable) {
                base['search'] = search.value
            }
        }
        return base
    })

    const openDialog = (item?: Row, index = -1): void => {
        editedIndex.value = index
        editedItem.value = item ? ({ ...item } as Row) : props.defaultItem()
        formRef.value?.resetValidation?.()
        // Snapshot the freshly-loaded working copy as the clean baseline for dirty-tracking.
        capture()
        dialog.value = true
    }

    // Guard the cancel/Escape path against unsaved edits. save() itself is left in charge of
    // closing (it closes in uncontrolled mode and defers to the caller in server mode), so the
    // prompt's "Save and Close" routes through it rather than force-closing here.
    const { confirmVisible, capture, requestClose, continueEditing, discardAndClose } = useUnsavedChanges({
        getState: () => editedItem.value,
        close: () => {
            dialog.value = false
        }
    })

    const confirmSaveAndClose = async (): Promise<void> => {
        confirmVisible.value = false
        await save()
    }

    const save = async (): Promise<void> => {
        const result = await formRef.value?.validate()
        if (result && !result.valid) {
            return
        }
        const isNew = editedIndex.value === -1

        if (props.server) {
            // Caller persists and closes the dialog.
            emit('save', editedItem.value, { isNew })
            return
        }

        const list = [...model.value]
        if (isNew) {
            list.push({ ...editedItem.value })
        } else {
            list[editedIndex.value] = { ...editedItem.value }
        }
        model.value = list
        emit('save', editedItem.value, { isNew })
        dialog.value = false
    }

    const remove = (item: Row, index: number): void => {
        if (props.server) {
            emit('delete', item, index)
            return
        }
        const list = [...model.value]
        list.splice(index, 1)
        model.value = list
        emit('delete', item, index)
    }

    const move = (index: number, offset: number): void => {
        const target = index + offset
        const list = [...model.value]
        if (target < 0 || target >= list.length) {
            return
        }
        const [moved] = list.splice(index, 1)
        if (!moved) {
            return
        }
        list.splice(target, 0, moved)
        model.value = list
    }
</script>
