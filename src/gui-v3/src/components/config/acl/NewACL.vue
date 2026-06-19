<template>
    <v-dialog v-model="dialog" max-width="900" persistent scrollable>
        <template #activator="{ props: activatorProps }">
            <AddNewButton :show="canCreate" v-bind="activatorProps" />
        </template>

        <v-card>
            <v-card-title>
                <span class="text-h5">
                    {{ isEdit ? t('acl.edit') : t('acl.add_new') }}
                </span>
            </v-card-title>

            <v-card-text>
                <v-form ref="formRef" @submit.prevent="handleSubmit">
                    <v-text-field
                        v-model="localItem.name"
                        :label="t('acl.name')"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                    />

                    <v-textarea
                        v-model="localItem.description"
                        :label="t('acl.description')"
                        variant="outlined"
                        density="comfortable"
                        rows="3"
                        class="mb-3"
                        :disabled="saving"
                    />

                    <v-select
                        v-model="localItem.item_type"
                        :label="t('acl.item_type')"
                        :items="itemTypes"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving"
                        @update:model-value="onItemTypeChange"
                    />

                    <v-select
                        v-model="localItem.item_id"
                        :label="t('acl.item')"
                        :items="itemOptions"
                        item-title="name"
                        item-value="id"
                        variant="outlined"
                        density="comfortable"
                        :loading="loadingItems"
                        :rules="[(v) => !!v || t('error.required')]"
                        :disabled="saving || !localItem.item_type"
                    />

                    <!-- Permission flags -->
                    <div class="d-flex ga-8 mb-2">
                        <v-checkbox v-model="localItem.see" :label="t('acl.see')" hide-details :disabled="saving" />
                        <v-checkbox v-model="localItem.access" :label="t('acl.access')" hide-details :disabled="saving" />
                        <v-checkbox v-model="localItem.modify" :label="t('acl.modify')" hide-details :disabled="saving" />
                        <v-checkbox v-model="localItem.everyone" :label="t('acl.everyone')" hide-details :disabled="saving" class="ms-auto" />
                    </div>

                    <EntitySelectTable
                        v-model="selectedUsers"
                        :title="t('acl.users')"
                        :items="users"
                        :headers="userHeaders"
                        :loading="loadingRecipients"
                        :disabled="saving || localItem.everyone"
                    />

                    <EntitySelectTable
                        v-model="selectedRoles"
                        :title="t('acl.roles')"
                        :items="roles"
                        :headers="roleHeaders"
                        :loading="loadingRecipients"
                        :disabled="saving || localItem.everyone"
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
                    {{ t('acl.error') }}
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
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { useAuth } from '@/composables/useAuth'
    import {
        createNewACLEntry,
        updateACLEntry,
        getAllCollectorsNodes,
        getAllOSINTSources,
        getAllOSINTSourceGroups,
        getAllReportItemTypes,
        getAllProductTypes,
        getAllWordLists,
        getAllUsers,
        getAllRoles
    } from '@/api/config'

    type ACLItemType = 'COLLECTOR' | 'OSINT_SOURCE' | 'OSINT_SOURCE_GROUP' | 'REPORT_ITEM_TYPE' | 'PRODUCT_TYPE' | 'WORD_LIST'

    type ACLItem = {
        id: string | number | null
        name: string
        description: string
        item_type: ACLItemType | ''
        item_id: string | number | null
        everyone: boolean
        see: boolean
        access: boolean
        modify: boolean
        [key: string]: unknown
    }

    type ACLItemTypeOption = {
        title: string
        value: ACLItemType
    }

    type ACLTargetItem = {
        id: string
        name: string
    }

    type UserOption = {
        id: string | number
        username: string
        name: string
    }

    type RoleOption = {
        id: string | number
        name: string
        description: string
    }

    type TableHeader = {
        title: string
        key: string
        sortable: boolean
    }

    type IdSelection = Array<string | number>

    type ListResponse = {
        data?: {
            items?: Array<Record<string, unknown>>
        }
    }

    type FormValidationResult = {
        valid: boolean
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            editItem?: Record<string, unknown> | null
        }>(),
        {
            modelValue: false,
            editItem: null
        }
    )

    const emit = defineEmits<{
        (e: 'saved'): void
        (e: 'update:modelValue', value: boolean): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)
    const dialog = ref(false)

    const itemTypes: ACLItemTypeOption[] = [
        { title: 'Collector', value: 'COLLECTOR' },
        { title: 'OSINT Source', value: 'OSINT_SOURCE' },
        { title: 'OSINT Source Group', value: 'OSINT_SOURCE_GROUP' },
        { title: 'Report Item Type', value: 'REPORT_ITEM_TYPE' },
        { title: 'Product Type', value: 'PRODUCT_TYPE' },
        { title: 'Word List', value: 'WORD_LIST' }
    ]

    const defaultItem: ACLItem = {
        id: null,
        name: '',
        description: '',
        item_type: '',
        item_id: null,
        everyone: false,
        see: false,
        access: false,
        modify: false
    }

    const localItem = ref<ACLItem>({ ...defaultItem })
    const isEdit = computed(() => !!localItem.value.id)

    const canCreate = computed(() => checkPermission('CONFIG_ACL_CREATE'))

    // Recipients (users / roles) the ACL is granted to.
    const users = ref<UserOption[]>([])
    const roles = ref<RoleOption[]>([])
    const selectedUsers = ref<IdSelection>([])
    const selectedRoles = ref<IdSelection>([])
    const loadingRecipients = ref(false)

    const userHeaders: TableHeader[] = [
        { title: t('user.username'), key: 'username', sortable: true },
        { title: t('user.name'), key: 'name', sortable: false }
    ]

    const roleHeaders: TableHeader[] = [
        { title: t('role.name'), key: 'name', sortable: true },
        { title: t('role.description'), key: 'description', sortable: false }
    ]

    // Selectable target items per ACL item type.
    const collectors = ref<ACLTargetItem[]>([])
    const osintSources = ref<ACLTargetItem[]>([])
    const osintSourceGroups = ref<ACLTargetItem[]>([])
    const reportItemTypes = ref<ACLTargetItem[]>([])
    const productTypes = ref<ACLTargetItem[]>([])
    const wordLists = ref<ACLTargetItem[]>([])
    const loadingItems = ref(false)

    // The list of selectable items for the currently chosen item type.
    const itemOptions = computed<ACLTargetItem[]>(() => {
        switch (localItem.value.item_type) {
            case 'COLLECTOR':
                return collectors.value
            case 'OSINT_SOURCE':
                return osintSources.value
            case 'OSINT_SOURCE_GROUP':
                return osintSourceGroups.value
            case 'REPORT_ITEM_TYPE':
                return reportItemTypes.value
            case 'PRODUCT_TYPE':
                return productTypes.value
            case 'WORD_LIST':
                return wordLists.value
            default:
                return []
        }
    })

    const extractItems = (response: unknown): Array<Record<string, unknown>> => (response as ListResponse).data?.items || []

    const loadItemSources = async (): Promise<void> => {
        loadingItems.value = true
        try {
            const [nodesResp, osintResp, groupsResp, reportResp, productResp, wordResp] = await Promise.all([
                getAllCollectorsNodes({ search: '' }),
                getAllOSINTSources({ search: '' }),
                getAllOSINTSourceGroups({ search: '' }),
                getAllReportItemTypes({ search: '' }),
                getAllProductTypes({ search: '' }),
                getAllWordLists({ search: '' })
            ])

            // Collectors are nested inside collector nodes.
            const flatCollectors: ACLTargetItem[] = []
            for (const node of extractItems(nodesResp)) {
                const nodeCollectors = (node['collectors'] as Array<{ id: string | number; name?: string }>) || []
                for (const collector of nodeCollectors) {
                    flatCollectors.push({ id: String(collector.id), name: collector.name || '' })
                }
            }
            collectors.value = flatCollectors

            osintSources.value = extractItems(osintResp).map((v) => ({ id: String(v['id']), name: String(v['name'] ?? '') }))
            osintSourceGroups.value = extractItems(groupsResp).map((v) => ({ id: String(v['id']), name: String(v['name'] ?? '') }))
            reportItemTypes.value = extractItems(reportResp).map((v) => ({
                id: String(v['id']),
                name: String(v['title'] ?? v['name'] ?? '')
            }))
            productTypes.value = extractItems(productResp).map((v) => ({ id: String(v['id']), name: String(v['title'] ?? v['name'] ?? '') }))
            wordLists.value = extractItems(wordResp).map((v) => ({ id: String(v['id']), name: String(v['name'] ?? '') }))
        } catch (error) {
            console.error('Error loading ACL item sources:', error)
        } finally {
            loadingItems.value = false
        }
    }

    const loadRecipients = async (): Promise<void> => {
        loadingRecipients.value = true
        try {
            const [usersResp, rolesResp] = await Promise.all([getAllUsers({ search: '' }), getAllRoles({ search: '' })])
            users.value = extractItems(usersResp).map((v) => ({
                id: v['id'] as string | number,
                username: String(v['username'] ?? ''),
                name: String(v['name'] ?? '')
            }))
            roles.value = extractItems(rolesResp).map((v) => ({
                id: v['id'] as string | number,
                name: String(v['name'] ?? ''),
                description: String(v['description'] ?? '')
            }))
        } catch (error) {
            console.error('Error loading ACL recipients:', error)
        } finally {
            loadingRecipients.value = false
        }
    }

    onMounted(() => {
        loadItemSources()
        loadRecipients()
    })

    // Clear the selected item when the user picks a different item type.
    function onItemTypeChange(): void {
        localItem.value.item_id = null
    }

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
            const payload = {
                name: localItem.value.name,
                description: localItem.value.description,
                item_type: localItem.value.item_type,
                item_id: localItem.value.item_id,
                everyone: localItem.value.everyone,
                see: localItem.value.see,
                access: localItem.value.access,
                modify: localItem.value.modify,
                users: selectedUsers.value.map((id) => ({ id })),
                roles: selectedRoles.value.map((id) => ({ id }))
            }
            if (isEdit.value) {
                await updateACLEntry({ ...payload, id: localItem.value.id })
            } else {
                // The backend requires an id key but ignores its value on create (it generates one).
                await createNewACLEntry({ ...payload, id: -1 })
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
        selectedUsers.value = []
        selectedRoles.value = []
        dialog.value = false
    }

    watch(
        () => props.editItem,
        (newItem) => {
            if (newItem && Object.keys(newItem).length > 0) {
                const incoming = newItem as Partial<ACLItem>
                localItem.value = { ...defaultItem, ...incoming }
                selectedUsers.value = Array.isArray(incoming['users'])
                    ? (incoming['users'] as Array<{ id: string | number }>).map((u) => u.id)
                    : []
                selectedRoles.value = Array.isArray(incoming['roles'])
                    ? (incoming['roles'] as Array<{ id: string | number }>).map((r) => r.id)
                    : []
                // Opening the dialog automatically when an item to edit is provided.
                dialog.value = true
            } else {
                localItem.value = { ...defaultItem }
                selectedUsers.value = []
                selectedRoles.value = []
            }
        },
        { immediate: true, deep: true }
    )

    watch(
        () => dialog.value,
        (newVal: boolean) => {
            if (!newVal) {
                showValidationError.value = false
                showError.value = false
                saving.value = false
                formRef.value?.reset()
                localItem.value = { ...defaultItem }
                selectedUsers.value = []
                selectedRoles.value = []
            }
            emit('update:modelValue', newVal)
        }
    )
</script>
