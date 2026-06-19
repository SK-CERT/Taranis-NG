<template>
    <v-dialog v-model="dialog" max-width="900" persistent scrollable>
        <template #activator="{ props: activatorProps }">
            <AddNewButton :show="canCreate" v-bind="activatorProps" />
        </template>

        <v-card>
            <v-card-title>
                <span class="text-h5">
                    {{ isEdit ? t('role.edit') : t('role.add_new') }}
                </span>
            </v-card-title>

            <v-card-text>
                <v-form ref="formRef" @submit.prevent="handleSubmit">
                    <v-text-field
                        v-model="localItem.name"
                        :label="t('role.title')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('role.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        :disabled="saving"
                    />

                    <!-- Permissions Selection -->
                    <EntitySelectTable
                        v-model="selectedPermissions"
                        :title="t('role.permissions')"
                        :items="permissions"
                        :headers="permissionHeaders"
                        :loading="loadingPermissions"
                        :disabled="saving"
                    />
                </v-form>

                <v-alert
                    v-if="showValidationError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showValidationError = false"
                >
                    {{ t('error.validation') }}
                </v-alert>

                <v-alert v-if="showError" type="error" variant="tonal" class="mt-4" closable @click:close="showError = false">
                    {{ t('role.error') }}
                </v-alert>
            </v-card-text>

            <v-card-actions>
                <v-spacer />
                <v-btn color="grey" variant="text" :disabled="saving" @click="handleCancel">
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn color="primary" variant="text" :loading="saving" @click="handleSubmit">
                    <v-icon left>mdi-content-save</v-icon>
                    {{ t('common.save') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { createNewRole, updateRole, getAllPermissions } from '@/api/config'

    type SelectableEntity = {
        id: string | number
        name?: string
        description?: string
        [key: string]: unknown
    }

    type RoleItem = {
        id: string | number | null
        name: string
        description: string
        permissions: unknown[]
        [key: string]: unknown
    }

    type FormValidationResult = {
        valid: boolean
    }

    type TableHeader = {
        title: string
        key: string
        sortable: boolean
    }

    type IdSelection = Array<string | number>

    type ListResponse = {
        data?: {
            items?: SelectableEntity[]
        }
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Partial<RoleItem> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits(['update:modelValue', 'saved'])

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)

    const permissions = ref<SelectableEntity[]>([])
    const loadingPermissions = ref(false)
    const selectedPermissions = ref<IdSelection>([])

    const permissionHeaders: TableHeader[] = [
        { title: t('role.name'), key: 'name', sortable: true },
        { title: t('role.description'), key: 'description', sortable: false }
    ]

    const defaultItem: RoleItem = {
        id: null,
        name: '',
        description: '',
        permissions: []
    }

    const localItem = ref<RoleItem>({ ...defaultItem })

    const isEdit = computed(() => !!localItem.value.id)
    const canCreate = computed(() => checkPermission('CONFIG_ROLE_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_ROLE_UPDATE') || !isEdit.value)

    const loadPermissions = async (): Promise<void> => {
        loadingPermissions.value = true
        try {
            const response = await getAllPermissions({ search: '' })
            permissions.value = (response as ListResponse).data?.items || []
        } catch (error) {
            console.error('Error loading permissions:', error)
        } finally {
            loadingPermissions.value = false
        }
    }

    onMounted(loadPermissions)

    async function handleSubmit(): Promise<void> {
        showValidationError.value = false
        showError.value = false

        const { valid } = (await formRef.value.validate()) as FormValidationResult
        if (!valid) {
            showValidationError.value = true
            return
        }

        saving.value = true
        try {
            const payload: RoleItem = {
                ...localItem.value,
                permissions: selectedPermissions.value.map((id) => ({ id }))
            }
            if (isEdit.value) {
                await updateRole(payload)
            } else {
                await createNewRole(payload)
            }
            emit('saved')
            handleCancel()
        } catch (error) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'common.error_saving' }
                })
            )
            showError.value = true
        } finally {
            saving.value = false
        }
    }

    function handleCancel(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        localItem.value = { ...defaultItem }
        selectedPermissions.value = []
        dialog.value = false
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                localItem.value = { ...defaultItem, ...newItem }
                selectedPermissions.value = Array.isArray(newItem.permissions)
                    ? (newItem.permissions as SelectableEntity[]).map((perm) => perm.id)
                    : []
                // Opening the dialog automatically when an item to edit is provided.
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
                selectedPermissions.value = []
            }
        },
        { immediate: true, deep: true }
    )

    watch(
        () => dialog.value,
        (newVal) => {
            if (!newVal) {
                showValidationError.value = false
                showError.value = false
                saving.value = false
                formRef.value?.reset()
                localItem.value = { ...defaultItem }
                selectedPermissions.value = []
            }
            emit('update:modelValue', newVal)
        }
    )
</script>
