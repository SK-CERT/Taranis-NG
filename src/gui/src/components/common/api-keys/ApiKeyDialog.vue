<template>
    <v-dialog
        v-model="open"
        max-width="860"
        persistent
        scrollable
        @keydown.esc.stop="close"
    >
        <v-card data-test="api-key-dialog">
            <DialogToolbar
                :title="t(editing ? 'api_keys.edit_title' : 'api_keys.add_title')"
                :saving="saving"
                @cancel="close"
                @save="save"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    :disabled="saving"
                    @submit.prevent="save"
                >
                    <v-autocomplete
                        v-if="mode === 'admin' && !editing"
                        v-model="form.ownerId"
                        :items="ownerItems"
                        :label="t('api_keys.owner')"
                        :hint="t('api_keys.owner_hint')"
                        persistent-hint
                        :rules="[requiredOwner]"
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        data-test="api-key-owner"
                    />
                    <div
                        v-else-if="mode === 'admin' && item?.user"
                        class="text-body-2 mb-4"
                    >
                        <span class="text-medium-emphasis me-1">{{ t('api_keys.owner') }}:</span>
                        <bdi dir="auto">{{ item.user.name || item.user.username }}</bdi>
                        (<bdi dir="ltr">{{ item.user.username }}</bdi
                        >)
                    </div>

                    <v-text-field
                        v-model="form.name"
                        :label="t('api_keys.name')"
                        :rules="[requiredText, maxLength(100)]"
                        :spellcheck="spellcheck"
                        counter="100"
                        variant="outlined"
                        density="comfortable"
                        class="mb-2"
                        data-test="api-key-name"
                    />

                    <v-textarea
                        v-model="form.description"
                        :label="t('api_keys.description')"
                        :rules="[maxLength(500)]"
                        :spellcheck="spellcheck"
                        rows="2"
                        auto-grow
                        variant="outlined"
                        density="comfortable"
                        class="mb-2"
                        data-test="api-key-description"
                    />

                    <!-- Expiry: chosen once; a key that should last longer is replaced by a new one. -->
                    <v-row
                        v-if="!editing"
                        dense
                    >
                        <v-col
                            cols="12"
                            :md="form.expiry === 'custom' ? 6 : 12"
                        >
                            <v-select
                                v-model="form.expiry"
                                :items="expiryOptions"
                                :label="t('api_keys.expiry')"
                                :hint="expiryHint"
                                persistent-hint
                                variant="outlined"
                                density="comfortable"
                                data-test="api-key-expiry"
                            />
                        </v-col>
                        <v-col
                            v-if="form.expiry === 'custom'"
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="form.customDate"
                                type="date"
                                :label="t('api_keys.expiry_date')"
                                :min="minDate"
                                :max="maxDate"
                                :rules="[requiredText, withinMaxDate]"
                                variant="outlined"
                                density="comfortable"
                                data-test="api-key-expiry-date"
                            />
                        </v-col>
                    </v-row>
                    <v-alert
                        v-else
                        type="info"
                        variant="tonal"
                        density="compact"
                        class="mb-4"
                        data-test="api-key-expiry-readonly"
                    >
                        <strong>{{ t('api_keys.expires') }}:</strong>
                        {{ item?.expires_at ? formatDateTime(item.expires_at) : t('api_keys.never') }}.
                        {{ t('api_keys.expiry_readonly') }}
                    </v-alert>

                    <div class="text-subtitle-2 mt-4">{{ t('api_keys.scope') }}</div>
                    <v-radio-group
                        v-model="form.scope"
                        hide-details
                        class="mb-2"
                        data-test="api-key-scope-choice"
                    >
                        <v-radio
                            value="all"
                            :label="t(mode === 'self' ? 'api_keys.scope_all_self' : 'api_keys.scope_all')"
                        />
                        <v-radio
                            value="selected"
                            :label="t('api_keys.scope_selected')"
                        />
                    </v-radio-group>
                    <template v-if="form.scope === 'selected'">
                        <p class="text-caption text-medium-emphasis mb-0">{{ t('api_keys.scope_selected_hint') }}</p>
                        <EntitySelectTable
                            v-model="form.permissions"
                            :title="t('api_keys.scope')"
                            :items="permissionItems"
                            :headers="permissionHeaders"
                            :loading="loadingPermissions"
                            :disabled="saving"
                        />
                        <v-alert
                            v-if="scopeError"
                            type="error"
                            variant="tonal"
                            density="compact"
                            class="mb-4"
                        >
                            {{ t('api_keys.scope_none_selected') }}
                        </v-alert>
                    </template>

                    <v-textarea
                        v-model="form.allowedIps"
                        :label="t('api_keys.allowed_ips')"
                        :hint="t('api_keys.allowed_ips_hint')"
                        persistent-hint
                        :rules="[allowlistRule]"
                        rows="3"
                        auto-grow
                        dir="ltr"
                        spellcheck="false"
                        autocomplete="off"
                        variant="outlined"
                        density="comfortable"
                        class="mt-4 api-key-dialog__ips"
                        data-test="api-key-allowed-ips"
                    />
                    <div
                        v-if="clientIp"
                        class="d-flex align-center flex-wrap ga-2 mt-1"
                    >
                        <span
                            v-if="clientIpPublic"
                            class="text-body-2 text-medium-emphasis"
                        >
                            {{ t('api_keys.your_ip', { ip: clientIp }) }}
                        </span>
                        <span
                            v-else
                            class="text-body-2 text-medium-emphasis"
                            data-test="api-key-ip-not-public"
                        >
                            {{ t('api_keys.your_ip_not_public', { ip: clientIp }) }}
                        </span>
                        <v-btn
                            v-if="clientIpPublic"
                            size="small"
                            variant="tonal"
                            prepend-icon="mdi-plus"
                            :disabled="saving || ipAlreadyListed"
                            data-test="api-key-add-my-ip"
                            @click="addMyIp"
                        >
                            {{ t('api_keys.add_my_ip') }}
                        </v-btn>
                    </div>
                    <v-alert
                        v-if="policy.site_allowlist_active"
                        type="info"
                        variant="tonal"
                        density="compact"
                        class="mt-3"
                    >
                        {{ t('api_keys.allowed_ips_site') }}
                    </v-alert>
                </v-form>

                <v-alert
                    v-if="errorMessage"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    data-test="api-key-error"
                >
                    <bdi dir="auto">{{ errorMessage }}</bdi>
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import EntitySelectTable from '@/components/common/EntitySelectTable.vue'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { createApiKey, getApiKeyPermissions, updateApiKey } from '@/api/config'
    import { createMyApiKey, updateMyApiKey } from '@/api/user'
    import {
        DEFAULT_EXPIRY_DAYS,
        EXPIRY_PRESETS,
        apiErrorMessage,
        dateInDays,
        expiryAtEndOfDay,
        expiryInDays,
        invalidAllowlistEntries,
        nonPublicAllowlistEntries,
        parseAllowlist,
        toDateInput,
        type ApiKeyItem,
        type ApiKeyOwner,
        type ApiKeyPayload,
        type ApiKeyPermission,
        type ApiKeyPolicy,
        type ApiKeySaved
    } from './apiKeys'

    const props = withDefaults(
        defineProps<{
            modelValue: boolean
            /** The key to edit; null creates one. */
            item?: ApiKeyItem | null
            /** admin: any user's keys (Access Management); self: the signed-in user's own. */
            mode: 'admin' | 'self'
            policy: ApiKeyPolicy
            clientIp?: string | null
            /** Whether the caller's address is public; only public addresses may be listed. */
            clientIpPublic?: boolean
            owners?: ApiKeyOwner[]
            /** The permissions a self-service key can be limited to. */
            availablePermissions?: ApiKeyPermission[]
        }>(),
        {
            item: null,
            clientIp: null,
            clientIpPublic: false,
            owners: () => [],
            availablePermissions: () => []
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'saved', value: ApiKeySaved): void
    }>()

    type ExpiryChoice = `${(typeof EXPIRY_PRESETS)[number]}` | 'max' | 'custom' | 'never'

    const { t } = useI18n()
    const spellcheck = useSpellcheck()
    const { formatDate, formatDateTime } = useLocaleFormatters()

    const open = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })
    const editing = computed(() => Boolean(props.item?.id))
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }> } | null>(null)
    const saving = ref(false)
    const errorMessage = ref('')
    const scopeError = ref(false)
    const loadingPermissions = ref(false)
    const loadedPermissions = ref<ApiKeyPermission[]>([])

    const form = ref({
        ownerId: null as number | null,
        name: '',
        description: '',
        expiry: String(DEFAULT_EXPIRY_DAYS) as ExpiryChoice,
        customDate: '',
        scope: 'all' as 'all' | 'selected',
        permissions: [] as Array<string | number>,
        allowedIps: ''
    })

    const requireExpiry = computed(() => props.policy.require_expiry || Boolean(props.policy.max_days))
    const maxDays = computed(() => props.policy.max_days || null)

    const expiryOptions = computed(() => {
        const options: { value: ExpiryChoice; title: string }[] = EXPIRY_PRESETS.filter(
            (days) => !maxDays.value || days <= maxDays.value
        ).map((days) => ({ value: String(days) as ExpiryChoice, title: t(`api_keys.expiry_${days}`) }))
        if (maxDays.value && !(EXPIRY_PRESETS as readonly number[]).includes(maxDays.value)) {
            options.push({ value: 'max', title: t('api_keys.expiry_max', { date: formatDate(expiryInDays(maxDays.value)) }) })
        }
        options.push({ value: 'custom', title: t('api_keys.expiry_custom') })
        if (!requireExpiry.value) options.push({ value: 'never', title: t('api_keys.expiry_never') })
        return options
    })

    // 90 days, or the longest the policy allows when that is shorter.
    const defaultExpiry = (): ExpiryChoice => {
        const values = expiryOptions.value.map((option) => option.value)
        const preferred = String(DEFAULT_EXPIRY_DAYS) as ExpiryChoice
        if (values.includes(preferred)) return preferred
        if (values.includes('max')) return 'max'
        const presets = values.filter((value) => /^\d+$/u.test(value))
        return presets[presets.length - 1] ?? 'custom'
    }

    const expiresAt = computed<string | null>(() => {
        const choice = form.value.expiry
        if (choice === 'never') return null
        if (choice === 'custom') return expiryAtEndOfDay(form.value.customDate)
        if (choice === 'max') return maxDays.value ? expiryInDays(maxDays.value) : null
        return expiryInDays(Number(choice))
    })

    const expiryHint = computed(() => {
        if (form.value.expiry === 'never') return ''
        if (form.value.expiry === 'custom')
            return maxDays.value ? t('api_keys.expiry_latest', { date: formatDate(expiryInDays(maxDays.value)) }) : ''
        return expiresAt.value ? t('api_keys.expiry_until', { date: formatDateTime(expiresAt.value) }) : ''
    })

    const minDate = computed(() => toDateInput(Date.now()))
    const maxDate = computed(() => (maxDays.value ? dateInDays(maxDays.value) : undefined))

    // A key of an account that is not active would be refused, so only active users are offered.
    const ownerItems = computed(() =>
        props.owners
            .filter((owner) => !owner.status || owner.status === 'active')
            .map((owner) => ({ value: owner.id, title: owner.name ? `${owner.name} (${owner.username})` : owner.username }))
    )
    const ownerId = computed(() => (editing.value ? props.item?.user_id : form.value.ownerId) ?? null)

    const permissionItems = computed(() =>
        (props.mode === 'self' ? props.availablePermissions : loadedPermissions.value).map((permission) => ({
            id: permission.id,
            name: permission.name || permission.id,
            description: permission.description || ''
        }))
    )
    const permissionHeaders = computed(() => [
        { title: t('api_keys.permission'), key: 'name' },
        { title: t('api_keys.permission_description'), key: 'description', sortable: false }
    ])

    const ipAlreadyListed = computed(() => Boolean(props.clientIp && parseAllowlist(form.value.allowedIps).includes(props.clientIp)))

    const requiredText = (value: string): true | string => Boolean(value?.trim()) || t('error.required')
    const requiredOwner = (value: number | null): true | string => Boolean(value) || t('error.required')
    const maxLength =
        (limit: number) =>
        (value: string): true | string =>
            (value || '').length <= limit || t('api_keys.too_long', { limit })
    const withinMaxDate = (value: string): true | string =>
        !maxDate.value || !value || value <= maxDate.value || t('api_keys.expiry_too_late')
    const allowlistRule = (value: string): true | string => {
        const invalid = invalidAllowlistEntries(value)
        if (invalid.length) return t('api_keys.allowed_ips_invalid', { entries: invalid.join(', ') })
        const notPublic = nonPublicAllowlistEntries(value)
        if (notPublic.length) return t('api_keys.allowed_ips_not_public', { entries: notPublic.join(', ') })
        if (props.policy.require_allowlist && parseAllowlist(value).length === 0) return t('api_keys.allowed_ips_required')
        return true
    }

    const addMyIp = (): void => {
        if (!props.clientIp || !props.clientIpPublic || ipAlreadyListed.value) return
        const current = form.value.allowedIps.trimEnd()
        form.value.allowedIps = current ? `${current}\n${props.clientIp}` : props.clientIp
    }

    const loadPermissions = async (userId: number | null): Promise<void> => {
        if (props.mode !== 'admin' || !userId) {
            loadedPermissions.value = []
            return
        }
        loadingPermissions.value = true
        try {
            const response = (await getApiKeyPermissions(userId)) as { data: { items: ApiKeyPermission[] } }
            if (ownerId.value === userId) loadedPermissions.value = response.data.items || []
        } catch (error) {
            console.error('Error loading the permissions of the API key owner:', error)
            loadedPermissions.value = []
        } finally {
            loadingPermissions.value = false
        }
    }

    const reset = (): void => {
        const item = props.item
        errorMessage.value = ''
        scopeError.value = false
        form.value = {
            ownerId: null,
            name: item?.name || '',
            description: item?.description || '',
            expiry: 'never',
            customDate: '',
            scope: item?.restricted ? 'selected' : 'all',
            permissions: item?.permissions.map((permission) => permission.id) || [],
            allowedIps: (item?.allowed_ips || []).join('\n')
        }
        form.value.expiry = defaultExpiry()
        loadedPermissions.value = []
        if (editing.value) loadPermissions(item?.user_id ?? null)
    }

    watch(
        () => props.modelValue,
        (visible) => {
            if (visible) reset()
        },
        { immediate: true }
    )

    watch(
        () => form.value.ownerId,
        (userId) => {
            if (!editing.value) {
                form.value.permissions = []
                loadPermissions(userId)
            }
        }
    )

    const payload = (): ApiKeyPayload => {
        const restricted = form.value.scope === 'selected'
        const body: ApiKeyPayload = {
            name: form.value.name.trim(),
            description: form.value.description.trim(),
            restricted,
            permissions: restricted ? form.value.permissions.map(String) : [],
            allowed_ips: parseAllowlist(form.value.allowedIps)
        }
        if (!editing.value) {
            body.expires_at = expiresAt.value
            if (props.mode === 'admin' && form.value.ownerId) body.user_id = form.value.ownerId
        }
        return body
    }

    const save = async (): Promise<void> => {
        errorMessage.value = ''
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        scopeError.value = form.value.scope === 'selected' && form.value.permissions.length === 0
        if (!valid || scopeError.value) return

        saving.value = true
        try {
            const body = payload()
            const id = props.item?.id
            let response: { data: ApiKeySaved }
            if (props.mode === 'admin') {
                response = (id ? await updateApiKey(id, body) : await createApiKey(body)) as { data: ApiKeySaved }
            } else {
                response = (id ? await updateMyApiKey(id, body) : await createMyApiKey(body)) as { data: ApiKeySaved }
            }
            emit('saved', response.data)
            open.value = false
        } catch (error) {
            errorMessage.value = apiErrorMessage(error) || t('api_keys.error')
        } finally {
            saving.value = false
        }
    }

    const close = (): void => {
        if (!saving.value) open.value = false
    }
</script>

<style scoped>
    .api-key-dialog__ips :deep(textarea) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
</style>
