<template>
    <v-dialog
        v-model="open"
        max-width="900"
        persistent
        scrollable
    >
        <v-card>
            <DialogToolbar
                :title="t(editing ? 'asset_group.edit' : 'asset_group.add_new')"
                :saving="saving"
                @cancel="close"
                @save="save"
            />
            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="save"
                >
                    <v-text-field
                        v-model="form.name"
                        :label="t('asset_group.name')"
                        :rules="[required]"
                        variant="outlined"
                    />
                    <v-textarea
                        v-model="form.description"
                        :label="t('asset_group.description')"
                        variant="outlined"
                        rows="3"
                    />
                    <v-data-table
                        v-model="selectedUsers"
                        :headers="userHeaders"
                        :items="users"
                        item-value="id"
                        show-select
                        :items-per-page="5"
                        class="mb-4"
                    >
                        <template #top
                            ><v-toolbar-title class="pa-3">{{ t('asset_group.allowed_users') }}</v-toolbar-title></template
                        >
                    </v-data-table>
                    <v-data-table
                        v-model="selectedTemplates"
                        :headers="templateHeaders"
                        :items="templates"
                        item-value="id"
                        show-select
                        :items-per-page="5"
                    >
                        <template #top
                            ><v-toolbar-title class="pa-3">{{ t('asset_group.notification_templates') }}</v-toolbar-title></template
                        >
                    </v-data-table>
                </v-form>
                <v-alert
                    v-if="error"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    >{{ t('asset_group.error') }}</v-alert
                >
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { createNewAssetGroup, getAllNotificationTemplates, updateAssetGroup } from '@/api/assets'
    import { getAllExternalUsers } from '@/api/config'
    import type { AssetGroup, Id, NotificationTemplate, UserReference } from '@/types/assets'

    const props = defineProps<{ modelValue: boolean; group?: AssetGroup | null }>()
    const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>()
    const { t } = useI18n()
    const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
    const editing = computed(() => Boolean(props.group?.id))
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }> } | null>(null)
    const form = ref({ name: '', description: '' })
    const users = ref<UserReference[]>([])
    const templates = ref<NotificationTemplate[]>([])
    const selectedUsers = ref<Id[]>([])
    const selectedTemplates = ref<Id[]>([])
    const saving = ref(false)
    const error = ref(false)
    const userHeaders = computed(() => [
        { title: t('external_user.username'), key: 'username' },
        { title: t('external_user.name'), key: 'name' }
    ])
    const templateHeaders = computed(() => [
        { title: t('notification_template.name'), key: 'name' },
        { title: t('notification_template.description'), key: 'description' }
    ])
    const required = (value: string): true | string => Boolean(value?.trim()) || t('error.required')
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    watch(open, async (visible) => {
        if (!visible) return
        form.value = { name: props.group?.name || '', description: props.group?.description || '' }
        selectedUsers.value = (props.group?.users || []).map((item) => item.id)
        selectedTemplates.value = (props.group?.templates || []).map((item) => item.id)
        error.value = false
        try {
            const [usersResponse, templatesResponse] = await Promise.all([
                getAllExternalUsers({ search: '' }) as Promise<{ data?: { items?: UserReference[] } }>,
                getAllNotificationTemplates({ search: '' }) as Promise<{ data?: { items?: NotificationTemplate[] } }>
            ])
            users.value = usersResponse.data?.items || []
            templates.value = templatesResponse.data?.items || []
        } catch {
            users.value = []
            templates.value = []
            error.value = true
            notify('error', 'asset_group.load_error')
        }
    })

    const save = async (): Promise<void> => {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return
        saving.value = true
        error.value = false
        const payload: AssetGroup = {
            id: props.group?.id || '',
            ...form.value,
            users: selectedUsers.value.map((id) => ({ id })),
            templates: selectedTemplates.value.map((id) => ({ id }))
        }
        try {
            if (editing.value) await updateAssetGroup(payload)
            else await createNewAssetGroup(payload)
            notify('success', editing.value ? 'asset_group.successful_edit' : 'asset_group.successful')
            emit('saved')
            open.value = false
        } catch {
            error.value = true
            notify('error', 'asset_group.error')
        } finally {
            saving.value = false
        }
    }
    const close = (): void => {
        open.value = false
    }
</script>
