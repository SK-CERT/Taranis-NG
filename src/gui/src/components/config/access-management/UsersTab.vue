<template>
    <v-container fluid>
        <v-card>
            <!-- Toolbar -->
            <v-card-text>
                <v-row>
                    <v-col cols="6">
                        <SearchField
                            v-model="search"
                            :width="350"
                        />
                    </v-col>
                    <v-col cols="2">
                        <v-select
                            v-model="statusFilter"
                            :items="statusFilterOptions"
                            :label="t('access_management.users.status')"
                            density="compact"
                            variant="outlined"
                            hide-details
                            clearable
                        />
                    </v-col>
                    <v-col
                        cols="4"
                        class="text-end"
                    >
                        <NewUser
                            :edit-item="editItem"
                            @saved="handleSaved"
                            @update:model-value="onDialogChange"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <!-- Data Table -->
            <v-data-table
                ref="tableRef"
                :headers="headers"
                :aria-busy="loading"
                :items="filteredUsers"
                :items-per-page="-1"
                :search="search"
                :row-props="rowProps"
                item-key="id"
                class="elevation-1"
            >
                <template
                    v-if="loading"
                    #body
                >
                    <TableSkeletonRows
                        :columns="headers"
                        :cells="{
                            username: { width: 120 },
                            name: { width: 140 },
                            roles: { type: 'chip', width: 64 },
                            organizations: { type: 'chip', width: 100 },
                            last_login_at: { width: 170 },
                            login_methods: { type: 'chip', width: 64 },
                            actions: { type: 'actions', width: 90 }
                        }"
                        :action-count="3"
                    />
                </template>
                <template #item.username="{ item }">
                    <strong>{{ asUserItem(item).username }}</strong>
                </template>

                <template #item.name="{ item }">
                    {{ asUserItem(item).name }}
                </template>

                <template #item.roles="{ item }">
                    <v-chip
                        v-for="role in asUserItem(item).roles || []"
                        :key="role.id"
                        size="small"
                        class="me-1"
                        variant="tonal"
                    >
                        {{ role.name }}
                    </v-chip>
                </template>

                <template #item.last_login_at="{ item }">
                    <span
                        v-if="asUserItem(item).last_login_at"
                        :title="asUserItem(item).last_login_at || ''"
                    >
                        {{ formatDateTime(asUserItem(item).last_login_at as string) }}
                    </span>
                    <span
                        v-else
                        class="text-medium-emphasis"
                        >&ndash;</span
                    >
                </template>

                <template #item.organizations="{ item }">
                    <v-chip
                        v-for="org in asUserItem(item).organizations || []"
                        :key="org.id"
                        size="small"
                        class="me-1"
                    >
                        {{ org.name }}
                    </v-chip>
                </template>

                <template #item.login_methods="{ item }">
                    <v-chip
                        v-if="asUserItem(item).has_password"
                        size="small"
                        class="me-1"
                        color="primary"
                        variant="tonal"
                    >
                        {{ t('access_management.users.local_password') }}
                    </v-chip>
                    <v-chip
                        v-for="identity in asUserItem(item).identities || []"
                        :key="identity.id"
                        size="small"
                        class="me-1"
                        variant="tonal"
                    >
                        {{ identity.provider_name }}
                    </v-chip>
                    <!-- The tooltip is styled like a card of the current theme (see the style block),
                         so the authenticator icons, which follow the theme, sit on a matching background. -->
                    <v-tooltip
                        v-if="hasMfa(asUserItem(item))"
                        location="top"
                        content-class="user-mfa-tooltip elevation-4"
                    >
                        <template #activator="{ props: tooltipProps }">
                            <v-icon
                                v-bind="tooltipProps"
                                size="small"
                                color="success"
                                tabindex="0"
                                :aria-label="t('access_management.users.mfa_enabled')"
                                data-test="user-mfa-badge"
                                >mdi-shield-key</v-icon
                            >
                        </template>
                        <div
                            class="user-mfa-summary"
                            data-test="user-mfa-summary"
                        >
                            <div class="user-mfa-summary__title">{{ t('access_management.users.mfa_enabled') }}</div>
                            <div
                                v-if="asUserItem(item).mfa?.totp"
                                class="user-mfa-summary__factor"
                                data-test="user-mfa-totp"
                            >
                                <v-icon size="20">mdi-cellphone-key</v-icon>
                                <span>{{ t('security.totp_title') }}</span>
                            </div>
                            <template v-if="(asUserItem(item).mfa?.passkeys ?? 0) > 0">
                                <div class="user-mfa-summary__factor">
                                    <v-icon size="20">mdi-fingerprint</v-icon>
                                    <span>{{ t('security.passkeys_title') }}</span>
                                </div>
                                <ul class="user-mfa-summary__passkeys">
                                    <li
                                        v-for="passkey in asUserItem(item).mfa?.passkey_details || []"
                                        :key="passkey.id"
                                        data-test="user-mfa-passkey"
                                    >
                                        <bdi
                                            dir="auto"
                                            class="user-mfa-summary__passkey-name"
                                            >{{ passkey.name }}</bdi
                                        >
                                        <PasskeyAuthenticator
                                            :aaguid="passkey.aaguid"
                                            :authenticator="passkey.authenticator"
                                            :lookup="passkey.authenticator_lookup !== false"
                                        />
                                    </li>
                                </ul>
                            </template>
                        </div>
                    </v-tooltip>
                </template>

                <template #item.actions="{ item }">
                    <v-btn
                        v-if="asUserItem(item).status === 'pending'"
                        color="success"
                        size="small"
                        variant="flat"
                        prepend-icon="mdi-account-check"
                        class="me-1"
                        @click="setStatus(asUserItem(item), 'active')"
                    >
                        {{ t('access_management.users.approve') }}
                    </v-btn>
                    <ActionButton
                        v-if="asUserItem(item).status === 'active'"
                        icon="mdi-account-off"
                        color="warning"
                        :title="t('access_management.users.disable')"
                        class="me-1"
                        @click="setStatus(asUserItem(item), 'disabled')"
                    />
                    <ActionButton
                        v-if="asUserItem(item).status === 'disabled'"
                        icon="mdi-account-reactivate"
                        color="success"
                        :title="t('access_management.users.enable')"
                        class="me-1"
                        @click="setStatus(asUserItem(item), 'active')"
                    />
                    <ActionButton
                        action="edit"
                        :title="t('common.edit')"
                        class="me-1"
                        @click="handleEdit(asUserItem(item))"
                    />
                    <ActionButton
                        v-if="canDelete"
                        action="delete"
                        :title="t('common.delete')"
                        @click="handleDelete(asUserItem(item))"
                    />
                </template>
            </v-data-table>
        </v-card>

        <ConfirmationDialog
            v-model="deleteDialog"
            :message="itemToDelete?.username || ''"
            max-width="600px"
            @confirm="confirmDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, ref, onMounted } from 'vue'
    import TableSkeletonRows from '@/components/common/TableSkeletonRows.vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { deleteUser, updateUserStatus } from '@/api/config'
    import NewUser from '@/components/config/access-management/NewUser.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import PasskeyAuthenticator from '@/components/common/PasskeyAuthenticator.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { notifyDeleteError } from '@/utils/deleteError'
    import type { PasskeySummary } from '@/types/auth'

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
        align?: 'start' | 'end' | 'center'
    }

    type OrganizationItem = {
        id: string | number
        name?: string
    }

    type UserIdentity = {
        id: string | number
        auth_provider_id?: number
        provider_name?: string
        provider_kind?: string
        external_username?: string
        last_login_at?: string | null
    }

    type RoleItem = {
        id: string | number
        name?: string
    }

    type UserItem = {
        id: string | number
        username?: string
        name?: string
        status?: string
        roles?: RoleItem[]
        last_login_at?: string | null
        organizations?: OrganizationItem[]
        identities?: UserIdentity[]
        has_password?: boolean
        mfa?: { totp?: boolean; passkeys?: number; passkey_details?: PasskeySummary[] }
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()
    const { formatDateTime } = useLocaleFormatters()
    const canDelete = computed(() => checkPermission('CONFIG_USER_DELETE'))

    const search = ref('')
    const statusFilter = ref<string | null>(null)
    const editItem = ref<UserItem | null>(null)
    const deleteDialog = ref(false)
    const itemToDelete = ref<UserItem | null>(null)

    const headers: HeaderEntry[] = [
        { title: t('access_management.users.username'), key: 'username' },
        { title: t('access_management.users.name'), key: 'name' },
        { title: t('access_management.users.roles'), key: 'roles', sortable: false },
        { title: t('access_management.users.organizations'), key: 'organizations' },
        { title: t('access_management.users.last_login'), key: 'last_login_at' },
        { title: t('access_management.users.login_methods'), key: 'login_methods', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false, align: 'end' }
    ]

    const statusFilterOptions = computed(() => [
        { title: t('access_management.users.statuses.pending'), value: 'pending' },
        { title: t('access_management.users.statuses.active'), value: 'active' },
        { title: t('access_management.users.statuses.disabled'), value: 'disabled' }
    ])

    const asUserItem = (item: unknown): UserItem => item as UserItem

    const filteredUsers = computed(() => {
        const items = configStore.users.items as UserItem[]
        if (!statusFilter.value) {
            return items
        }
        return items.filter((user) => (user.status || 'active') === statusFilter.value)
    })

    // A disabled account is dimmed rather than labelled, the same treatment disabled OSINT
    // sources get: the row stays readable on hover, and the enable action is still in reach.
    const rowProps = ({ item }: { item: unknown }): Record<string, unknown> => ({
        class: (item as UserItem).status === 'disabled' ? 'user-disabled' : ''
    })

    const hasMfa = (user: UserItem): boolean => !!(user.mfa?.totp || (user.mfa?.passkeys ?? 0) > 0)

    const loading = ref(true)
    let pendingLoads = 0

    const loadData = async (): Promise<void> => {
        pendingLoads++
        loading.value = true
        try {
            await configStore.loadUsers({ search: search.value })
        } catch (error) {
            console.error('Error loading users:', error)
        } finally {
            pendingLoads--
            loading.value = pendingLoads > 0
        }
    }

    const setStatus = async (item: UserItem, status: string): Promise<void> => {
        try {
            await updateUserStatus(item.id, status)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'common.updated_successfully' } }))
            await loadData()
        } catch (error) {
            console.error('Error changing user status:', error)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'access_management.users.status_error' } }))
        }
    }

    const handleEdit = (item: UserItem): void => {
        // Setting editItem triggers NewUser's watcher to open its dialog in edit mode.
        editItem.value = item
    }

    const handleDelete = (item: UserItem): void => {
        if (!canDelete.value) return
        itemToDelete.value = item
        deleteDialog.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        if (!canDelete.value || !itemToDelete.value) {
            return
        }
        try {
            await deleteUser(itemToDelete.value)
            await loadData()
        } catch (error) {
            console.error('Error deleting user:', error)
            notifyDeleteError(error, { inUse: 'access_management.users.removed_error' })
        } finally {
            itemToDelete.value = null
        }
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

    onMounted(() => {
        loadData()
    })
</script>

<style scoped>
    /* Matches the disabled OSINT source rows: dimmed at rest, full contrast under the pointer
       so a disabled account can still be read and acted on. */
    :deep(.user-disabled) {
        opacity: 0.55;
    }

    :deep(.user-disabled:hover) {
        opacity: 1;
    }

    /* The tooltip is teleported out of this component, hence :global. App.vue paints every
       tooltip in inverted colours (with !important) and caps it at 320px; a card of the current
       theme keeps the theme-matched authenticator icons legible, and the AAGUIDs need the width. */
    :global(.v-tooltip > .v-overlay__content.user-mfa-tooltip) {
        max-width: none;
        border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
        background: rgb(var(--v-theme-surface)) !important;
        color: rgb(var(--v-theme-on-surface)) !important;
        padding: 8px 12px;
    }

    .user-mfa-summary {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .user-mfa-summary__title {
        font-weight: 600;
    }

    .user-mfa-summary__factor {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .user-mfa-summary__passkeys {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin: 0;
        padding-inline-start: 28px;
        list-style: none;
    }

    .user-mfa-summary__passkeys li {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .user-mfa-summary__passkey-name {
        font-weight: 500;
    }
</style>
