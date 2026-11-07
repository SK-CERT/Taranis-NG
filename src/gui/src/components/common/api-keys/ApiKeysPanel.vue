<template>
    <div class="api-keys-panel">
        <div
            class="d-flex align-center flex-wrap ga-3 mb-3"
            :class="{ 'px-4 pt-4': mode === 'self' }"
        >
            <SearchField
                v-if="mode === 'admin'"
                v-model="search"
                :width="320"
            />
            <v-autocomplete
                v-if="mode === 'admin'"
                v-model="ownerFilter"
                :items="ownerItems"
                :label="t('api_keys.owner')"
                :placeholder="t('api_keys.all_users')"
                density="compact"
                variant="outlined"
                hide-details
                clearable
                class="api-keys-panel__filter"
                data-test="api-keys-owner-filter"
            />
            <v-select
                v-model="statusFilter"
                :items="statusItems"
                :label="t('api_keys.status')"
                density="compact"
                variant="outlined"
                hide-details
                clearable
                class="api-keys-panel__filter"
                data-test="api-keys-status-filter"
            />
            <v-spacer />
            <AddNewButton
                :show="canCreate"
                label="api_keys.add"
                data-test="api-keys-add"
                @click="openCreate"
            />
        </div>

        <v-alert
            v-if="loadError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-3"
            :class="{ 'mx-4': mode === 'self' }"
        >
            {{ t('api_keys.load_error') }}
        </v-alert>

        <ApiKeysTable
            :items="visibleItems"
            :loading="loading"
            :show-owner="mode === 'admin'"
            :compact="mode === 'self'"
            :can-update="canUpdate"
            :can-delete="canDelete"
            :busy-id="togglingId"
            @edit="openEdit"
            @toggle="toggle"
            @delete="askDelete"
        />

        <ApiKeyDialog
            v-model="dialogOpen"
            :item="editItem"
            :mode="mode"
            :policy="policy"
            :client-ip="clientIp"
            :client-ip-public="clientIpPublic"
            :owners="owners"
            :available-permissions="availablePermissions"
            @saved="onSaved"
        />

        <ApiKeyRevealDialog
            v-model="revealOpen"
            :api-key="revealedKey"
            :name="revealedName"
            @update:model-value="onRevealClosed"
        />

        <ConfirmationDialog
            v-model="deleteOpen"
            max-width="600px"
            @confirm="confirmDelete"
        >
            {{ t('api_keys.delete_message', { name: toDelete?.name || '' }) }}
        </ConfirmationDialog>
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import SearchField from '@/components/common/SearchField.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useOptimisticToggle } from '@/composables/useOptimisticToggle'
    import { notifyDeleteError } from '@/utils/deleteError'
    import { deleteApiKey, getAllApiKeys, updateApiKey } from '@/api/config'
    import { deleteMyApiKey, getMyApiKeys, updateMyApiKey } from '@/api/user'
    import ApiKeyDialog from './ApiKeyDialog.vue'
    import ApiKeyRevealDialog from './ApiKeyRevealDialog.vue'
    import ApiKeysTable from './ApiKeysTable.vue'
    import {
        DEFAULT_POLICY,
        apiErrorMessage,
        apiKeyStatus,
        type ApiKeyItem,
        type ApiKeyListResponse,
        type ApiKeyOwner,
        type ApiKeyPermission,
        type ApiKeyPolicy,
        type ApiKeySaved,
        type ApiKeyStatus
    } from './apiKeys'

    const props = defineProps<{
        /** admin: every user's keys (Access Management); self: the signed-in user's own (User settings). */
        mode: 'admin' | 'self'
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const items = ref<ApiKeyItem[]>([])
    const policy = ref<ApiKeyPolicy>({ ...DEFAULT_POLICY })
    const clientIp = ref<string | null>(null)
    const clientIpPublic = ref(false)
    const owners = ref<ApiKeyOwner[]>([])
    const availablePermissions = ref<ApiKeyPermission[]>([])
    const loading = ref(true)
    const loadError = ref(false)

    // SearchField's clear button sets null at runtime; the filter reads it as ''.
    const search = ref('')
    const ownerFilter = ref<number | null>(null)
    const statusFilter = ref<ApiKeyStatus | null>(null)

    const dialogOpen = ref(false)
    const editItem = ref<ApiKeyItem | null>(null)
    const revealOpen = ref(false)
    const revealedKey = ref('')
    const revealedName = ref('')
    const deleteOpen = ref(false)
    const toDelete = ref<ApiKeyItem | null>(null)

    // Self-service is gated by the tab (MY_API_KEYS_MANAGE); the admin tab by each action's permission.
    const canCreate = computed(() => props.mode === 'self' || checkPermission('CONFIG_API_KEY_CREATE'))
    const canUpdate = computed(() => props.mode === 'self' || checkPermission('CONFIG_API_KEY_UPDATE'))
    const canDelete = computed(() => props.mode === 'self' || checkPermission('CONFIG_API_KEY_DELETE'))

    const ownerItems = computed(() =>
        owners.value.map((owner) => ({ value: owner.id, title: owner.name ? `${owner.name} (${owner.username})` : owner.username }))
    )
    const statusItems = computed(() => [
        { value: 'active', title: t('api_keys.status_active') },
        { value: 'disabled', title: t('api_keys.status_disabled') },
        { value: 'expired', title: t('api_keys.status_expired') }
    ])

    const visibleItems = computed(() => {
        const needle = (search.value || '').trim().toLowerCase()
        return items.value.filter((item) => {
            if (ownerFilter.value && item.user_id !== ownerFilter.value) return false
            if (statusFilter.value && apiKeyStatus(item) !== statusFilter.value) return false
            if (!needle) return true
            return [item.name, item.description, item.key_prefix, item.user?.username, item.user?.name].some((value) =>
                (value || '').toLowerCase().includes(needle)
            )
        })
    })

    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    // The busy row while its enable/disable is saving; the composable owns it.
    const { busyId: togglingId, toggle: optimisticToggle } = useOptimisticToggle()

    // Only the first load shows the skeleton rows. Re-reading the list after an action is quiet:
    // the table keeps showing what it has, already updated in place, instead of flashing the
    // loading animation for a change the user just made.
    let pendingLoads = 0
    const loadData = async ({ quiet = false }: { quiet?: boolean } = {}): Promise<void> => {
        pendingLoads++
        if (!quiet) loading.value = true
        loadError.value = false
        try {
            const response = (props.mode === 'admin' ? await getAllApiKeys() : await getMyApiKeys()) as { data: ApiKeyListResponse }
            const data = response.data
            items.value = data.items || []
            policy.value = { ...DEFAULT_POLICY, ...(data.policy || {}) }
            clientIp.value = data.client_ip || null
            clientIpPublic.value = Boolean(data.client_ip_public)
            owners.value = data.owners || []
            availablePermissions.value = data.available_permissions || []
        } catch (error) {
            console.error('Error loading API keys:', error)
            if (!quiet) loadError.value = true
        } finally {
            pendingLoads--
            if (!quiet) loading.value = pendingLoads > 0
        }
    }

    const reloadQuietly = (): Promise<void> => loadData({ quiet: true })

    /** The list's own row for a key, which is what gets changed in place. */
    const rowOf = (item: ApiKeyItem): ApiKeyItem | undefined => items.value.find((row) => row.id === item.id)

    const replaceRow = (saved: ApiKeyItem): void => {
        const index = items.value.findIndex((row) => row.id === saved.id)
        if (index >= 0) items.value[index] = saved
    }

    const openCreate = (): void => {
        editItem.value = null
        dialogOpen.value = true
    }

    const openEdit = (item: ApiKeyItem): void => {
        editItem.value = item
        dialogOpen.value = true
    }

    const onSaved = (saved: ApiKeySaved): void => {
        if (saved.key) {
            revealedKey.value = saved.key
            revealedName.value = saved.item?.name || ''
            revealOpen.value = true
            notify('success', 'api_keys.created_success')
        } else {
            if (saved.item) replaceRow(saved.item)
            notify('success', 'common.updated_successfully')
        }
        reloadQuietly()
    }

    // Forget the plaintext as soon as its dialog closes.
    const onRevealClosed = (visible: boolean): void => {
        if (!visible) {
            revealedKey.value = ''
            revealedName.value = ''
        }
    }

    // Flipped at once and put back if the save fails, like the other enable switches.
    const toggle = async (item: ApiKeyItem): Promise<void> => {
        const row = rowOf(item)
        if (!row || togglingId.value !== null) return
        const enabled = !row.enabled
        await optimisticToggle(row, enabled, {
            save: async (value) => {
                if (props.mode === 'admin') await updateApiKey(row.id, { enabled: value })
                else await updateMyApiKey(row.id, { enabled: value })
                notify('success', value ? 'api_keys.enabled_success' : 'api_keys.disabled_success')
            },
            reload: reloadQuietly,
            onError: (error) => {
                console.error('Error changing an API key:', error, apiErrorMessage(error))
                notify('error', 'common.error_updating')
            }
        })
    }

    const askDelete = (item: ApiKeyItem): void => {
        toDelete.value = item
        deleteOpen.value = true
    }

    const confirmDelete = async (): Promise<void> => {
        const item = toDelete.value
        if (!item) return
        try {
            if (props.mode === 'admin') await deleteApiKey(item.id)
            else await deleteMyApiKey(item.id)
            items.value = items.value.filter((row) => row.id !== item.id)
            notify('success', 'common.deleted_successfully')
        } catch (error) {
            console.error('Error deleting an API key:', error)
            notifyDeleteError(error)
        } finally {
            toDelete.value = null
        }
        await reloadQuietly()
    }

    watch(
        () => props.mode,
        () => loadData()
    )

    onMounted(() => {
        loadData()
    })
</script>

<style scoped>
    .api-keys-panel__filter {
        max-width: 240px;
        min-width: 180px;
    }
</style>
