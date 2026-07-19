<template>
    <v-dialog
        v-model="dialog"
        max-width="600"
        persistent
        scrollable
        @keydown.esc="requestClose"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canCreate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('public_web.nodes.edit') : t('public_web.nodes.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-text-field
                        v-model="localItem.name"
                        :label="t('public_web.nodes.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('public_web.nodes.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_url"
                        :label="t('public_web.nodes.api_url')"
                        :hint="t('public_web.nodes.api_url_hint')"
                        persistent-hint
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-text-field
                        v-model="localItem.api_key"
                        :label="t('settings.api_key')"
                        :type="showApiKey ? 'text' : 'password'"
                        :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                        variant="outlined"
                        density="comfortable"
                        :hint="t('public_web.nodes.api_key_hint')"
                        persistent-hint
                        :disabled="saving"
                        @click:append-inner="showApiKey = !showApiKey"
                    />
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
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import { createNewPublicWebNode, updatePublicWebNode } from '@/api/config'

    type NodeItem = {
        id: string | number | null
        name: string
        description: string
        api_url: string
        api_key: string
        [key: string]: unknown
    }

    type FormValidationResult = { valid: boolean }

    const props = withDefaults(
        defineProps<{
            editItem?: Partial<NodeItem> | null
        }>(),
        { editItem: null }
    )

    const emit = defineEmits<{ (e: 'saved'): void }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const saving = ref(false)
    const dialog = ref(false)
    const showApiKey = ref(false)

    const defaultItem: NodeItem = { id: null, name: '', description: '', api_url: '', api_key: '' }
    const localItem = ref<NodeItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_CREATE'))

    async function persist(): Promise<boolean> {
        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            return false
        }
        saving.value = true
        try {
            if (isEdit.value) {
                await updatePublicWebNode(localItem.value)
            } else {
                await createNewPublicWebNode({ ...localItem.value, id: -1 })
            }
            emit('saved')
            return true
        } catch (error) {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
            return false
        } finally {
            saving.value = false
        }
    }

    function closeDialog(): void {
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        showApiKey.value = false
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => localItem.value,
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
            }
        },
        { immediate: true, deep: true }
    )

    watch(
        () => dialog.value,
        (newVal: boolean) => {
            if (!newVal) {
                saving.value = false
            } else {
                capture()
            }
        }
    )
</script>
