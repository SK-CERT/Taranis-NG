<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="configStore.publicWebTemplates.total_count"
            total-count-title="public_web.templates.total_count"
            @update-filter="handleFilterUpdate"
        >
            <template #addbutton>
                <NewPublicWebTemplate
                    :edit-item="editItem"
                    :templates="templates"
                    :public-webs="publicWebs"
                    @saved="handleSaved"
                />
            </template>
        </ToolbarFilter>

        <v-table
            density="compact"
            class="mt-2"
        >
            <thead>
                <tr>
                    <th>{{ t('public_web.templates.name') }}</th>
                    <th>{{ t('public_web.templates.kind') }}</th>
                    <th>{{ t('public_web.templates.target') }}</th>
                    <th>{{ t('public_web.templates.webs') }}</th>
                    <th>{{ t('public_web.templates.require_tlp_clear') }}</th>
                    <th>{{ t('public_web.templates.updated') }}</th>
                    <th class="text-end">{{ t('public_web.webs.actions') }}</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="template in templates"
                    :key="template.id ?? template.name"
                    data-test="template-row"
                >
                    <td>
                        <bdi dir="auto">{{ template.name }}</bdi>
                    </td>
                    <td>
                        {{
                            template.product_preset_id != null ? t('public_web.templates.kind_product') : t('public_web.templates.kind_item')
                        }}
                    </td>
                    <td>
                        <bdi dir="auto">{{ template.target_title }}</bdi>
                    </td>
                    <td data-test="template-webs-cell">
                        <bdi
                            v-if="template.web_names && template.web_names.length"
                            dir="auto"
                            >{{ template.web_names.join(', ') }}</bdi
                        >
                        <span
                            v-else
                            class="text-medium-emphasis"
                            >{{ t('public_web.templates.every_web') }}</span
                        >
                    </td>
                    <td>
                        <v-icon
                            v-if="template.product_preset_id != null"
                            :icon="template.require_tlp_clear ? 'mdi-check' : 'mdi-minus'"
                            size="small"
                        />
                    </td>
                    <td class="text-medium-emphasis">
                        {{ template.updated_at }}
                        <span v-if="template.updated_by"
                            >· <bdi dir="auto">{{ template.updated_by }}</bdi></span
                        >
                    </td>
                    <td class="text-end">
                        <v-btn
                            v-if="canUpdate"
                            icon="mdi-pencil"
                            size="x-small"
                            variant="text"
                            :title="t('common.edit')"
                            @click="edit(template)"
                        />
                        <v-btn
                            v-if="canUpdate"
                            icon="mdi-delete"
                            size="x-small"
                            variant="text"
                            color="error"
                            :title="t('common.delete')"
                            @click="askDelete(template)"
                        />
                    </td>
                </tr>
                <tr v-if="!templates.length">
                    <td
                        colspan="7"
                        class="text-medium-emphasis"
                    >
                        {{ t('public_web.templates.none') }}
                    </td>
                </tr>
            </tbody>
        </v-table>

        <section
            class="mt-8"
            data-test="builtin-templates"
        >
            <h3 class="text-title-medium px-4 mb-1">{{ t('public_web.templates.builtin_title') }}</h3>
            <p class="text-body-medium text-medium-emphasis px-4 mb-2">{{ t('public_web.templates.builtin_intro') }}</p>
            <v-table density="compact">
                <thead>
                    <tr>
                        <th class="text-no-wrap">{{ t('public_web.templates.builtin_in_use') }}</th>
                        <th>{{ t('public_web.templates.name') }}</th>
                        <th>{{ t('public_web.templates.builtin_used_for') }}</th>
                        <th>{{ t('public_web.templates.updated') }}</th>
                        <th class="text-end">{{ t('public_web.webs.actions') }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="builtin in shownBuiltins"
                        :key="builtin.id"
                        data-test="builtin-row"
                    >
                        <td>
                            <v-switch
                                v-if="builtin.can_disable"
                                :model-value="builtin.enabled"
                                color="primary"
                                density="compact"
                                hide-details
                                :disabled="!canUpdate || togglingBuiltin === builtin.id"
                                :loading="togglingBuiltin === builtin.id"
                                :aria-label="builtin.name"
                                data-test="builtin-switch"
                                @update:model-value="(value) => toggleBuiltin(builtin, value)"
                            />
                            <v-icon
                                v-else
                                icon="mdi-lock-outline"
                                size="small"
                                class="ms-2"
                                :title="t('public_web.templates.builtin_always_on')"
                                data-test="builtin-always-on"
                            />
                        </td>
                        <td>
                            <code :class="{ 'text-disabled': !builtin.enabled }">{{ builtin.name }}</code>
                        </td>
                        <td class="builtin-used-for">
                            <div :class="{ 'text-disabled': !builtin.enabled }">{{ usedFor(builtin) }}</div>
                            <div
                                v-if="!builtin.can_disable"
                                class="text-body-small text-medium-emphasis"
                            >
                                {{ t('public_web.templates.builtin_always_on') }}
                            </div>
                            <div
                                v-else-if="!builtin.enabled && offEffect(builtin)"
                                class="text-body-small text-warning"
                                data-test="builtin-off-effect"
                            >
                                {{ offEffect(builtin) }}
                            </div>
                        </td>
                        <td class="text-medium-emphasis">
                            {{ builtin.updated_at }}
                            <span v-if="builtin.updated_by"
                                >· <bdi dir="auto">{{ builtin.updated_by }}</bdi></span
                            >
                        </td>
                        <td class="text-end">
                            <v-btn
                                icon="mdi-eye-outline"
                                size="x-small"
                                variant="text"
                                :title="t('public_web.templates.builtin_view')"
                                data-test="builtin-view"
                                @click="viewBuiltin(builtin)"
                            />
                        </td>
                    </tr>
                    <tr v-if="!shownBuiltins.length">
                        <td
                            colspan="5"
                            class="text-medium-emphasis"
                        >
                            {{ builtinsLoaded ? t('public_web.templates.builtin_none') : '' }}
                        </td>
                    </tr>
                </tbody>
            </v-table>
        </section>

        <BuiltinTemplateDialog
            v-model="builtinDialog"
            :template="viewedBuiltin"
            :used-for="viewedBuiltin ? usedFor(viewedBuiltin) : ''"
        />

        <ConfirmationDialog
            v-model="confirmVisible"
            :message="pendingDelete ? t('public_web.templates.confirm_delete', { name: pendingDelete.name }) : ''"
            @confirm="performDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useAuth } from '@/composables/useAuth'
    import { deletePublicWebTemplate, getBuiltinPublicWebTemplates, setBuiltinPublicWebTemplateEnabled } from '@/api/config'
    import { useOptimisticToggle } from '@/composables/useOptimisticToggle'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import BuiltinTemplateDialog from '@/components/config/public-web/BuiltinTemplateDialog.vue'
    import NewPublicWebTemplate from '@/components/config/public-web/NewPublicWebTemplate.vue'
    import type { PublicWebBuiltinTemplate, PublicWebTemplate } from '@/types/public-web-template'
    import { notifyDeleteError } from '@/utils/deleteError'

    type BuiltinRow = PublicWebBuiltinTemplate & { id: string }

    const { t, te } = useI18n()
    const configStore = useConfigStore()
    const { checkPermission } = useAuth()

    const filter = ref<{ search: string }>({ search: '' })
    const editItem = ref<PublicWebTemplate | null>(null)
    const confirmVisible = ref(false)
    const pendingDelete = ref<PublicWebTemplate | null>(null)

    const canUpdate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_UPDATE'))
    const templates = computed<PublicWebTemplate[]>(() => (configStore.publicWebTemplates.items as PublicWebTemplate[]) || [])
    // Served with the templates: the webs a template can be restricted to.
    const publicWebs = computed<Array<{ id: number; name: string }>>(
        () => (configStore.publicWebTemplates as { public_webs?: Array<{ id: number; name: string }> }).public_webs || []
    )

    async function load(): Promise<void> {
        try {
            await configStore.loadPublicWebTemplates(filter.value)
        } catch (error) {
            console.error('Error loading report templates:', error)
        }
    }

    function handleFilterUpdate(newFilter: { search: string }): void {
        filter.value = newFilter
        load()
    }

    // -- built-in templates ----------------------------------------------------------

    const builtins = ref<BuiltinRow[]>([])
    const builtinsLoaded = ref(false)
    const builtinDialog = ref(false)
    const viewedBuiltin = ref<BuiltinRow | null>(null)
    const { busyId: togglingBuiltin, toggle } = useOptimisticToggle()

    // Re-read quietly after a switch: the row already shows the new state.
    async function loadBuiltins(): Promise<void> {
        try {
            const response = (await getBuiltinPublicWebTemplates()) as { data?: { items?: PublicWebBuiltinTemplate[] } }
            builtins.value = (response.data?.items || []).map((builtin) => ({ ...builtin, id: builtin.name }))
        } catch (error) {
            console.error('Error loading the built-in report templates:', error)
        } finally {
            builtinsLoaded.value = true
        }
    }

    // `builtin/item_generic.html` -> `item_generic`; the macros file's leading underscore goes too.
    const stem = (builtin: PublicWebBuiltinTemplate): string =>
        builtin.name
            .replace(/^builtin\//u, '')
            .replace(/\.html$/u, '')
            .replace(/^_/u, '')

    function usedFor(builtin: PublicWebBuiltinTemplate): string {
        const key = `public_web.templates.builtin_use.${stem(builtin)}`
        return te(key) ? t(key) : ''
    }

    // What switching it off does, said while it is off.
    const OFF_EFFECTS: Record<string, string> = {
        product_vulnerability: 'product',
        item_vulnerability: 'item_specific',
        item_generic: 'item_generic'
    }

    function offEffect(builtin: PublicWebBuiltinTemplate): string {
        const effect = OFF_EFFECTS[stem(builtin)]
        return effect ? t(`public_web.templates.builtin_off.${effect}`) : ''
    }

    // The search narrows the built-ins too, as it does the custom templates (name or source).
    const shownBuiltins = computed<BuiltinRow[]>(() => {
        const needle = (filter.value.search || '').trim().toLowerCase()
        if (!needle) return builtins.value
        return builtins.value.filter((builtin) =>
            [builtin.name, builtin.source, usedFor(builtin)].some((text) => text.toLowerCase().includes(needle))
        )
    })

    async function toggleBuiltin(builtin: BuiltinRow, value: boolean | null): Promise<void> {
        await toggle(builtin, value !== false, {
            save: (enabled) => setBuiltinPublicWebTemplateEnabled(builtin.name, enabled),
            reload: loadBuiltins,
            onError: (error) => {
                console.error('Error switching a built-in report template:', error)
                window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_updating' } }))
            }
        })
    }

    function viewBuiltin(builtin: BuiltinRow): void {
        viewedBuiltin.value = builtin
        builtinDialog.value = true
    }

    function edit(template: PublicWebTemplate): void {
        // A fresh object per click, so the dialog's watcher sees every edit.
        editItem.value = { ...template }
    }

    function handleSaved(): void {
        editItem.value = null
        load()
    }

    function askDelete(template: PublicWebTemplate): void {
        pendingDelete.value = template
        confirmVisible.value = true
    }

    async function performDelete(): Promise<void> {
        if (!pendingDelete.value) return
        try {
            await deletePublicWebTemplate(pendingDelete.value)
            await load()
        } catch (error) {
            console.error('Error deleting report template:', error)
            notifyDeleteError(error)
        } finally {
            pendingDelete.value = null
        }
    }

    onMounted(() => {
        load()
        loadBuiltins()
    })
</script>

<style scoped>
    /* On a phone the table scrolls sideways rather than squeezing the description into a sliver. */
    .builtin-used-for {
        min-width: 18rem;
    }
</style>
