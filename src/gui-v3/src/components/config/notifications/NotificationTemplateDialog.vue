<template>
    <v-dialog
        v-model="open"
        max-width="900"
        persistent
        scrollable
    >
        <v-card>
            <DialogToolbar
                :title="t(editing ? 'notification_template.edit' : 'notification_template.add_new')"
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
                        :label="t('notification_template.name')"
                        :rules="[required]"
                        variant="outlined"
                    />
                    <v-textarea
                        v-model="form.description"
                        :label="t('notification_template.description')"
                        variant="outlined"
                        rows="2"
                    />
                    <v-text-field
                        v-model="form.message_title"
                        :label="t('notification_template.message_title')"
                        variant="outlined"
                    />
                    <label class="text-subtitle-2 d-block mb-2">{{ t('notification_template.message_body') }}</label>
                    <Editor
                        v-model="form.message_body"
                        editor-style="min-height: 220px"
                        class="mb-4"
                    />
                    <RecipientTable v-model="recipients" />
                </v-form>
                <v-alert
                    v-if="error"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    >{{ t('notification_template.error') }}</v-alert
                >
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import Editor from 'primevue/editor'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import RecipientTable from './RecipientTable.vue'
    import { createNewNotificationTemplate, updateNotificationTemplate } from '@/api/assets'
    import type { NotificationRecipient, NotificationTemplate } from '@/types/assets'
    const props = defineProps<{ modelValue: boolean; template?: NotificationTemplate | null }>()
    const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>()
    const { t } = useI18n()
    const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
    const editing = computed(() => Boolean(props.template?.id))
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }> } | null>(null)
    const form = ref({ name: '', description: '', message_title: '', message_body: '<p></p>' })
    const recipients = ref<NotificationRecipient[]>([])
    const saving = ref(false)
    const error = ref(false)
    const required = (value: string): true | string => Boolean(value?.trim()) || t('error.required')
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }
    watch(open, (visible) => {
        if (!visible) return
        form.value = {
            name: props.template?.name || '',
            description: props.template?.description || '',
            message_title: props.template?.message_title || '',
            message_body: props.template?.message_body || '<p></p>'
        }
        recipients.value = (props.template?.recipients || []).map((item) => ({ ...item }))
        error.value = false
    })
    const save = async (): Promise<void> => {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return
        saving.value = true
        error.value = false
        const payload: NotificationTemplate = { id: props.template?.id || 0, ...form.value, recipients: recipients.value }
        try {
            if (editing.value) await updateNotificationTemplate(payload)
            else await createNewNotificationTemplate(payload)
            notify('success', editing.value ? 'notification_template.successful_edit' : 'notification_template.successful')
            emit('saved')
            open.value = false
        } catch {
            error.value = true
            notify('error', 'notification_template.error')
        } finally {
            saving.value = false
        }
    }
    const close = (): void => {
        open.value = false
    }
</script>
