<template>
    <v-container fluid>
        <v-card>
            <v-card-text>
                <v-row>
                    <v-col cols="8">
                        <SearchField
                            v-model="search"
                            :width="350"
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-end"
                    >
                        <AddNewButton
                            :show="canCreate"
                            @click="addItem"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <v-data-table
                :headers="headers"
                :items="rows"
                :items-per-page="-1"
                :search="search"
                :loading="loading"
                item-key="id"
                class="elevation-1"
                data-test="tags-table"
            >
                <template #item.shown_name="{ item }">
                    <bdi dir="auto">{{ item.shown_name }}</bdi>
                </template>

                <template #item.color="{ item }">
                    <v-chip
                        v-if="item.color"
                        :color="item.color"
                        label
                    >
                        {{ item.color }}
                    </v-chip>
                </template>

                <template #item.icon="{ item }">
                    <v-icon
                        v-if="item.icon"
                        :color="item.color || undefined"
                    >
                        {{ item.icon }}
                    </v-icon>
                </template>

                <template #item.actions="{ item }">
                    <ActionButton
                        v-if="canUpdate"
                        action="edit"
                        :title="t('common.edit')"
                        class="me-1"
                        @click="editItem(item)"
                    />
                    <ActionButton
                        v-if="item.system_key"
                        action="lock"
                        :title="t('tags.built_in_hint')"
                    />
                    <ActionButton
                        v-else-if="canDelete"
                        action="delete"
                        :title="t('common.delete')"
                        @click="deleteItem(item)"
                    />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog
            v-model="dialogDelete"
            :message="tagName(editedItem)"
            max-width="500"
            @confirm="deleteRecord"
        />

        <!-- `persistent`: Escape goes only through requestClose (the unsaved-changes guard). -->
        <v-dialog
            v-model="dialogEdit"
            max-width="700"
            persistent
            scrollable
            @keydown.esc.stop="requestClose"
        >
            <v-card>
                <DialogToolbar
                    :title="editedItem.id === -1 ? t('tags.add_new') : t('tags.edit')"
                    :show-save="canSave"
                    :saving="saving"
                    @cancel="requestClose"
                    @save="saveAndClose"
                />
                <v-card-text>
                    <v-alert
                        v-if="editedItem.system_key"
                        type="info"
                        variant="tonal"
                        density="compact"
                        class="mb-3"
                    >
                        {{ t('tags.built_in_hint') }}
                    </v-alert>
                    <v-form
                        ref="formRef"
                        :disabled="!canSave"
                    >
                        <v-text-field
                            v-model="nameModel"
                            :spellcheck="spellcheck"
                            :label="t('tags.name')"
                            :disabled="!!editedItem.system_key"
                            variant="outlined"
                            density="comfortable"
                            class="mb-3"
                            dir="auto"
                            :rules="[(v) => !!v || t('error.required')]"
                            data-test="tag-name"
                        />
                        <v-textarea
                            v-model="editedItem.description"
                            :spellcheck="spellcheck"
                            :label="t('tags.description')"
                            variant="outlined"
                            density="comfortable"
                            rows="2"
                            class="mb-3"
                            dir="auto"
                        />
                        <v-row>
                            <v-col cols="6">
                                <div class="text-caption text-medium-emphasis mb-1 px-3">
                                    {{ t('tags.color') }}
                                </div>
                                <v-text-field
                                    v-model="editedItem.color"
                                    :aria-label="t('tags.color')"
                                    variant="outlined"
                                    type="color"
                                    density="comfortable"
                                    hide-details
                                />
                            </v-col>
                            <v-col cols="6">
                                <MdiIconPicker
                                    v-model="editedItem.icon"
                                    :label="t('tags.icon')"
                                    :disabled="!canSave"
                                />
                            </v-col>
                        </v-row>
                    </v-form>
                </v-card-text>
            </v-card>

            <UnsavedChangesDialog
                v-model="confirmVisible"
                @continue="continueEditing"
                @save="saveAndClose"
                @discard="discardAndClose"
            />
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import MdiIconPicker from '@/components/common/MdiIconPicker.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import { createTag, deleteTag, getAllTags, updateTag } from '@/api/config'
    import { useAuth } from '@/composables/useAuth'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { useTagsStore } from '@/stores/tags'

    /**
     * Configuration › Workflow › Tags: the tags people put on reports and products, and the built-in
     * ones Taranis sets (translation status, language not set). Built-in tags can be renamed and
     * restyled, not deleted; Tag Workflow switches them off.
     */

    type Tag = {
        id: number
        display_name: string
        description: string
        color: string
        icon: string
        system_key: string | null
    }

    const { t, locale } = useI18n()
    const spellcheck = useSpellcheck()
    const { checkPermission } = useAuth()
    const { tagName } = useTagLabels()
    const tagsStore = useTagsStore()

    const tags = ref<Tag[]>([])
    // Built-in tags are stored under their keys; the table lists, sorts and searches the names shown.
    const rows = computed(() =>
        tags.value
            .map((tag) => ({ ...tag, shown_name: tagName(tag) }))
            .sort((left, right) => left.shown_name.localeCompare(right.shown_name, String(locale.value)))
    )
    const loading = ref(false)
    const search = ref('')
    const dialogEdit = ref(false)
    const dialogDelete = ref(false)
    const saving = ref(false)
    const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

    // A data default stored on the new tag, not theme paint.
    const emptyTag = (): Tag => ({ id: -1, display_name: '', description: '', color: '#607D8B', icon: 'mdi-tag', system_key: null })
    const editedItem = ref<Tag>(emptyTag())
    // A built-in tag is named by its key, translated, like a built-in state: only its look changes.
    const nameModel = computed<string>({
        get: () =>
            editedItem.value.system_key
                ? tagName({ ...editedItem.value, display_name: editedItem.value.system_key })
                : editedItem.value.display_name,
        set: (value: string) => {
            if (!editedItem.value.system_key) editedItem.value.display_name = value
        }
    })

    const headers = [
        { title: t('tags.name'), key: 'shown_name' },
        { title: t('tags.description'), key: 'description' },
        { title: t('tags.color'), key: 'color' },
        { title: t('tags.icon'), key: 'icon' },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const canCreate = computed(() => checkPermission('CONFIG_WORKFLOW_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_WORKFLOW_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_WORKFLOW_DELETE'))
    const canSave = computed(() => (editedItem.value.id === -1 ? canCreate.value : canUpdate.value))

    const notify = (type: 'success' | 'error', loc: string, params?: Record<string, unknown>): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc, params } }))
    }

    async function load(): Promise<void> {
        loading.value = true
        try {
            const response = (await getAllTags()) as { data?: { items?: Tag[] } }
            tags.value = response.data?.items ?? []
        } finally {
            loading.value = false
        }
    }

    function addItem(): void {
        editedItem.value = emptyTag()
        dialogEdit.value = true
    }

    function editItem(item: Tag): void {
        editedItem.value = { ...item, description: item.description ?? '', color: item.color ?? '', icon: item.icon ?? '' }
        dialogEdit.value = true
    }

    function deleteItem(item: Tag): void {
        editedItem.value = { ...item }
        dialogDelete.value = true
    }

    async function persist(): Promise<boolean> {
        if (!canSave.value) return false
        const result = await formRef.value?.validate()
        if (result && !result.valid) return false
        saving.value = true
        try {
            const { id, display_name, description, color, icon } = editedItem.value
            const payload = { display_name, description, color, icon }
            if (id === -1) await createTag(payload)
            else await updateTag({ ...payload, id })
            tagsStore.invalidate()
            await load()
            return true
        } catch (error) {
            const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
            if (message) window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', message } }))
            else notify('error', 'common.error_saving')
            return false
        } finally {
            saving.value = false
        }
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => editedItem.value,
        save: persist,
        close: () => {
            dialogEdit.value = false
        }
    })

    watch(dialogEdit, (open) => {
        if (open) capture()
        else saving.value = false
    })

    async function deleteRecord(): Promise<void> {
        try {
            await deleteTag(editedItem.value)
            tagsStore.invalidate()
            await load()
        } catch (error) {
            const data = (error as { response?: { status?: number; data?: { usage_count?: number } } })?.response
            if (data?.status === 409) notify('error', 'tags.in_use', { count: data.data?.usage_count ?? 0 })
            else notify('error', 'common.error_deleting')
        } finally {
            dialogDelete.value = false
        }
    }

    onMounted(() => {
        if (checkPermission('CONFIG_WORKFLOW_ACCESS')) void load()
    })

    defineExpose({ load })
</script>
