<template>
    <v-dialog
        v-model="open"
        max-width="760"
        persistent
        scrollable
    >
        <v-card>
            <DialogToolbar
                :title="t(editing ? 'external_user.edit' : 'external_user.add_new')"
                :saving="saving"
                @cancel="close"
                @save="save"
            />
            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="save"
                >
                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                            ><v-text-field
                                v-model="form.username"
                                :label="t('external_user.username')"
                                :rules="[required]"
                                variant="outlined"
                        /></v-col>
                        <v-col
                            cols="12"
                            md="6"
                            ><v-text-field
                                v-model="form.name"
                                :label="t('external_user.name')"
                                variant="outlined"
                        /></v-col>
                        <v-col
                            cols="12"
                            md="6"
                            ><v-text-field
                                v-model="password"
                                :label="t('external_user.password')"
                                type="password"
                                :rules="editing && !password ? [] : [required]"
                                variant="outlined"
                        /></v-col>
                        <v-col
                            cols="12"
                            md="6"
                            ><v-text-field
                                v-model="passwordAgain"
                                :label="t('external_user.password_check')"
                                type="password"
                                :rules="[passwordMatches]"
                                variant="outlined"
                        /></v-col>
                    </v-row>
                    <v-data-table
                        v-model="selectedPermissions"
                        :headers="permissionHeaders"
                        :items="permissions"
                        item-value="id"
                        show-select
                        :items-per-page="-1"
                        hide-default-footer
                    >
                        <template #top
                            ><v-toolbar-title class="pa-3">{{ t('external_user.permissions') }}</v-toolbar-title></template
                        >
                    </v-data-table>
                </v-form>
                <v-alert
                    v-if="error"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    >{{ t('external_user.error') }}</v-alert
                >
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { createNewExternalUser, getAllExternalPermissions, updateExternalUser } from '@/api/config'

    type Permission = { id: number; name?: string; description?: string }
    type ExternalUser = { id?: number; username: string; name: string; permissions?: Permission[] }
    const props = defineProps<{ modelValue: boolean; user?: ExternalUser | null }>()
    const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>()
    const { t } = useI18n()
    const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
    const editing = computed(() => Boolean(props.user?.id))
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }> } | null>(null)
    const form = ref({ username: '', name: '' })
    const password = ref('')
    const passwordAgain = ref('')
    const permissions = ref<Permission[]>([])
    const selectedPermissions = ref<number[]>([])
    const saving = ref(false)
    const error = ref(false)
    const permissionHeaders = computed(() => [
        { title: t('external_user.permission_name'), key: 'name' },
        { title: t('external_user.permission_description'), key: 'description' }
    ])
    const required = (value: string): true | string => Boolean(value) || t('error.required')
    const passwordMatches = (value: string): true | string => value === password.value || t('external_user.password_mismatch')
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    watch(open, async (visible) => {
        if (!visible) return
        form.value = { username: props.user?.username || '', name: props.user?.name || '' }
        password.value = ''
        passwordAgain.value = ''
        selectedPermissions.value = (props.user?.permissions || []).map((item) => item.id)
        error.value = false
        try {
            const response = (await getAllExternalPermissions({ search: '' })) as { data?: { items?: Permission[] } }
            permissions.value = response.data?.items || []
        } catch {
            permissions.value = []
            error.value = true
            notify('error', 'external_user.load_error')
        }
    })

    const save = async (): Promise<void> => {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return
        saving.value = true
        error.value = false
        const payload = {
            id: props.user?.id,
            ...form.value,
            password: password.value || null,
            permissions: selectedPermissions.value.map((id) => ({ id })),
            roles: [],
            organizations: []
        }
        try {
            if (editing.value) await updateExternalUser(payload)
            else await createNewExternalUser(payload)
            notify('success', editing.value ? 'external_user.successful_edit' : 'external_user.successful')
            emit('saved')
            open.value = false
        } catch {
            error.value = true
            notify('error', 'external_user.error')
        } finally {
            saving.value = false
        }
    }
    const close = (): void => {
        open.value = false
    }
</script>
