<template>
    <v-container fluid>
        <v-card>
            <!-- Toolbar -->
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
                        class="text-right"
                    >
                        <NewAuthProvider
                            :edit-item="editItem"
                            @saved="handleSaved"
                            @update:model-value="onDialogChange"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table
                :headers="headers"
                :items="configStore.authProviders.items as AuthProviderItem[]"
                :search="search"
                :loading="loading"
                item-key="id"
                class="elevation-1"
            >
                <template #item.id="{ item }">
                    <code class="text-body-2 font-weight-medium">{{ item.id }}</code>
                </template>
                <template #item.name="{ item }">
                    <strong>{{ providerName(item) }}</strong>
                </template>
                <template #item.kind="{ item }">
                    <v-chip
                        size="small"
                        :color="kindColor(item.kind)"
                        variant="tonal"
                    >
                        {{ t(`auth_provider.kinds.${item.kind}`) }}
                    </v-chip>
                </template>
                <template #item.organization="{ item }">
                    {{ item.organization?.name || '-' }}
                </template>
                <template #item.provisioning_mode="{ item }">
                    <span v-if="['oidc', 'oauth2', 'saml', 'ldap'].includes(item.kind)">
                        {{ t(`auth_provider.provisioning.${item.provisioning_mode}`) }}
                    </span>
                    <span v-else>-</span>
                </template>
                <template #item.enabled="{ item }">
                    <v-icon
                        :color="item.enabled ? 'success' : 'grey'"
                        size="small"
                    >
                        {{ item.enabled ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                </template>
                <template #item.linked_identity_count="{ item }">
                    {{ item.linked_identity_count ?? 0 }}
                </template>
                <template #item.actions="{ item }">
                    <ActionButton
                        v-if="canUpdate"
                        action="edit"
                        :title="t('common.edit')"
                        class="mr-1"
                        @click="handleEdit(item)"
                    />
                    <ActionButton
                        v-if="canDelete && !isLocal(item)"
                        action="delete"
                        :title="t('common.delete')"
                        @click="askDelete(item)"
                    />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog
            v-model="deleteDialog"
            :message="deleteMessage"
            @confirm="confirmDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useAuth } from '@/composables/useAuth'
    import { useProviderDisplay } from '@/composables/useProviderDisplay'
    import { deleteAuthProvider } from '@/api/config'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import NewAuthProvider from '@/components/config/auth-providers/NewAuthProvider.vue'

    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const { isLocal, providerName } = useProviderDisplay()
    const configStore = useConfigStore()

    type AuthProviderItem = {
        id: number
        name: string
        kind: string
        enabled: boolean
        provisioning_mode: string
        organization?: { id: number; name?: string } | null
        linked_identity_count?: number
        [key: string]: unknown
    }

    const loading = ref(false)
    const search = ref('')
    const editItem = ref<AuthProviderItem | null>(null)
    const deleteDialog = ref(false)
    const deleteTarget = ref<AuthProviderItem | null>(null)

    const canUpdate = computed(() => checkPermission('CONFIG_AUTH_PROVIDER_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_AUTH_PROVIDER_DELETE'))

    const headers = computed(() => [
        { title: t('auth_provider.id'), key: 'id' },
        { title: t('auth_provider.name'), key: 'name' },
        { title: t('auth_provider.kind'), key: 'kind' },
        { title: t('auth_provider.organization'), key: 'organization', sortable: false },
        { title: t('auth_provider.provisioning_mode'), key: 'provisioning_mode', sortable: false },
        { title: t('auth_provider.enabled'), key: 'enabled' },
        { title: t('auth_provider.linked_users'), key: 'linked_identity_count', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' as const }
    ])

    const deleteMessage = computed(() => {
        if (!deleteTarget.value) {
            return ''
        }
        const count = deleteTarget.value.linked_identity_count ?? 0
        const name = providerName(deleteTarget.value)
        return count > 0 ? t('auth_provider.delete_message_linked', { name, count }) : t('auth_provider.delete_message', { name })
    })

    const kindColor = (kind: string): string => {
        const colors: Record<string, string> = {
            local: 'primary',
            oidc: 'orange',
            oauth2: 'red',
            saml: 'purple',
            ldap: 'green'
        }
        return colors[kind] || 'grey'
    }

    const loadData = async (): Promise<void> => {
        loading.value = true
        try {
            await configStore.loadAuthProviders({ search: '' })
        } catch (error) {
            console.error('Error loading auth providers:', error)
        } finally {
            loading.value = false
        }
    }

    const handleEdit = (item: AuthProviderItem): void => {
        // Setting editItem triggers NewAuthProvider's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleSaved = (): void => {
        editItem.value = null
        loadData()
    }

    // Reset editItem when the dialog closes so the same row can be edited again,
    // and so the Add New button opens a blank form.
    const onDialogChange = (open: boolean): void => {
        if (!open) {
            editItem.value = null
        }
    }

    const askDelete = (item: AuthProviderItem): void => {
        deleteTarget.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!deleteTarget.value) {
            return
        }
        try {
            await deleteAuthProvider(deleteTarget.value)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'auth_provider.removed' } }))
            await loadData()
        } catch (error) {
            console.error('Error deleting auth provider:', error)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'auth_provider.remove_error' } }))
        } finally {
            deleteTarget.value = null
            deleteDialog.value = false
        }
    }

    onMounted(() => {
        loadData()
    })
</script>
