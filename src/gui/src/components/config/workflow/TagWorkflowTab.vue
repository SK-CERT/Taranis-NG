<template>
    <v-container fluid>
        <v-card class="mt-4">
            <v-card-text>
                <v-row>
                    <v-col cols="6">
                        <v-select
                            v-model="filterEntityType"
                            :items="entityTypeItems"
                            :label="t('workflow.state_workflow.filter_by_entity_type')"
                            variant="outlined"
                            density="compact"
                            clearable
                            hide-details
                        />
                    </v-col>
                    <v-col
                        cols="6"
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
                :items="shownLinks"
                :items-per-page="-1"
                :loading="loading"
                item-key="id"
                class="elevation-1"
                data-test="tag-workflow-table"
            >
                <template #item.entity_type="{ item }">
                    <EntityTypeChip :entity-type="item.entity_type" />
                </template>
                <template #item.tag="{ item }">
                    <v-chip
                        v-if="item.tag"
                        :color="item.tag.color || undefined"
                        :prepend-icon="item.tag.icon || undefined"
                        label
                        size="small"
                        variant="flat"
                    >
                        <bdi dir="auto">{{ tagName(item.tag) }}</bdi>
                    </v-chip>
                </template>
                <template #item.is_active="{ item }">
                    <v-icon :color="item.is_active ? 'green' : 'error'">
                        {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
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
                        v-if="item.tag?.system_key"
                        action="lock"
                        :title="t('tags.built_in_link_hint')"
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
            :message="t('common.messagebox.delete_confirm_item')"
            max-width="500"
            @confirm="deleteRecord"
        />

        <v-dialog
            v-model="dialogEdit"
            max-width="600"
            persistent
            @keydown.esc.stop="dialogEdit = false"
        >
            <v-card>
                <DialogToolbar
                    :title="editedItem.id === -1 ? t('tags.add_link') : t('tags.edit_link')"
                    :show-save="editedItem.id === -1 ? canCreate : canUpdate"
                    :saving="saving"
                    :save-disabled="editedItem.id === -1 && (!editedItem.tag_id || !editedItem.entity_type)"
                    @cancel="dialogEdit = false"
                    @save="save"
                />
                <v-card-text>
                    <v-select
                        v-model="editedItem.entity_type"
                        :items="entityTypeItems"
                        :label="t('workflow.state_workflow.entity_type')"
                        :disabled="editedItem.id !== -1"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                    />
                    <v-select
                        v-model="editedItem.tag_id"
                        :items="tagItems"
                        :label="t('tags.tag')"
                        :disabled="editedItem.id !== -1"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        data-test="link-tag"
                    />
                    <v-text-field
                        v-model.number="editedItem.sort_order"
                        type="number"
                        :label="t('workflow.state_workflow.sort_order')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                    />
                    <v-switch
                        v-model="editedItem.is_active"
                        :label="t('workflow.state_workflow.is_active')"
                        color="primary"
                        hide-details
                    />
                </v-card-text>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import EntityTypeChip from '@/components/config/workflow/EntityTypeChip.vue'
    import { createTagEntityType, deleteTagEntityType, getAllTagEntityTypes, getAllTags, updateTagEntityType } from '@/api/config'
    import { useAuth } from '@/composables/useAuth'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useTagsStore, type OfferedTag } from '@/stores/tags'

    /**
     * Configuration › Workflow › Tag Workflow: which tags reports and products use, in which order,
     * and whether they are shown. A built-in tag stays linked and can only be switched off.
     */

    type Link = {
        id: number
        tag_id: number | null
        entity_type: string
        is_active: boolean
        sort_order: number
        tag?: OfferedTag | null
    }

    const ENTITY_TYPES = ['report_item', 'product'] as const

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const { tagName } = useTagLabels()
    const tagsStore = useTagsStore()

    const links = ref<Link[]>([])
    const tags = ref<OfferedTag[]>([])
    const loading = ref(false)
    const saving = ref(false)
    const filterEntityType = ref<string | null>(null)
    const dialogEdit = ref(false)
    const dialogDelete = ref(false)
    const emptyLink = (): Link => ({ id: -1, tag_id: null, entity_type: 'report_item', is_active: true, sort_order: 0 })
    const editedItem = ref<Link>(emptyLink())

    const headers = [
        { title: t('workflow.state_workflow.entity_type'), key: 'entity_type' },
        { title: t('tags.tag'), key: 'tag', sortable: false },
        { title: t('workflow.state_workflow.sort_order'), key: 'sort_order' },
        { title: t('workflow.state_workflow.is_active'), key: 'is_active' },
        { title: t('settings.actions'), key: 'actions', sortable: false }
    ]

    const canCreate = computed(() => checkPermission('CONFIG_WORKFLOW_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_WORKFLOW_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_WORKFLOW_DELETE'))

    const entityTypeItems = computed(() => ENTITY_TYPES.map((value) => ({ title: t(`workflow.entity_types.${value}`), value })))
    const shownLinks = computed(() => links.value.filter((link) => !filterEntityType.value || link.entity_type === filterEntityType.value))
    // Admin tags not linked to the chosen entity type yet; built-in ones are always linked.
    const tagItems = computed(() =>
        tags.value
            .filter((tag) => !tag.system_key)
            .filter((tag) => !links.value.some((link) => link.tag_id === tag.id && link.entity_type === editedItem.value.entity_type))
            .map((tag) => ({ title: tagName(tag), value: tag.id }))
    )

    const notifyError = (error: unknown, fallback: string): void => {
        const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
        window.dispatchEvent(
            new CustomEvent('notification', { detail: message ? { type: 'error', message } : { type: 'error', loc: fallback } })
        )
    }

    async function load(): Promise<void> {
        loading.value = true
        try {
            const [linkResponse, tagResponse] = (await Promise.all([getAllTagEntityTypes(), getAllTags()])) as Array<{
                data?: { items?: unknown[] }
            }>
            links.value = (linkResponse?.data?.items ?? []) as Link[]
            tags.value = (tagResponse?.data?.items ?? []) as OfferedTag[]
        } finally {
            loading.value = false
        }
    }

    function addItem(): void {
        editedItem.value = { ...emptyLink(), entity_type: filterEntityType.value ?? 'report_item' }
        dialogEdit.value = true
    }

    function editItem(item: Link): void {
        editedItem.value = { ...item }
        dialogEdit.value = true
    }

    function deleteItem(item: Link): void {
        editedItem.value = { ...item }
        dialogDelete.value = true
    }

    async function save(): Promise<void> {
        saving.value = true
        try {
            const { id, tag_id, entity_type, is_active, sort_order } = editedItem.value
            if (id === -1) await createTagEntityType({ tag_id, entity_type, is_active, sort_order })
            else await updateTagEntityType({ id, is_active, sort_order })
            tagsStore.invalidate()
            await load()
            dialogEdit.value = false
        } catch (error) {
            notifyError(error, 'common.error_saving')
        } finally {
            saving.value = false
        }
    }

    async function deleteRecord(): Promise<void> {
        try {
            await deleteTagEntityType(editedItem.value)
            tagsStore.invalidate()
            await load()
        } catch (error) {
            notifyError(error, 'common.error_saving')
        } finally {
            dialogDelete.value = false
        }
    }

    onMounted(() => {
        if (checkPermission('CONFIG_WORKFLOW_ACCESS')) void load()
    })

    defineExpose({ load, editedItem, save })
</script>
