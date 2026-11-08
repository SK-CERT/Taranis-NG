<template>
    <v-dialog
        v-model="dialog"
        max-width="1100"
        persistent
        scrollable
        @keydown.esc.stop="requestClose"
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                :show="canUpdate"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="isEdit ? t('public_web.templates.edit') : t('public_web.templates.add_new')"
                :saving="saving"
                @cancel="requestClose"
                @save="saveAndClose"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="saveAndClose"
                >
                    <v-row>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-text-field
                                v-model="localItem.name"
                                :label="t('public_web.templates.name')"
                                variant="outlined"
                                density="comfortable"
                                :rules="[(v) => !!v || t('error.required')]"
                                :disabled="saving"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-select
                                :model-value="kind"
                                :items="kindItems"
                                :label="t('public_web.templates.kind')"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving || isEdit"
                                data-test="template-kind"
                                @update:model-value="setKind"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="4"
                        >
                            <v-select
                                v-model="target"
                                :items="targetItems"
                                item-title="title"
                                item-value="id"
                                :label="
                                    kind === 'product' ? t('public_web.templates.product_preset') : t('public_web.templates.report_item_type')
                                "
                                :hint="t('public_web.templates.target_hint')"
                                persistent-hint
                                :loading="loadingTypes"
                                :rules="[(v) => v != null || t('error.required')]"
                                variant="outlined"
                                density="comfortable"
                                :disabled="saving"
                                data-test="template-target"
                            />
                        </v-col>
                    </v-row>

                    <!-- The webs it is for: none chosen, every web. A web another template of the same
                         product or type claims is not offered. -->
                    <v-select
                        v-model="localItem.public_web_ids"
                        :items="publicWebs"
                        item-title="name"
                        item-value="id"
                        :item-props="webItemProps"
                        :label="t('public_web.templates.webs')"
                        :hint="t('public_web.templates.webs_hint')"
                        :placeholder="t('public_web.templates.every_web')"
                        persistent-placeholder
                        persistent-hint
                        :rules="[everyWebRule]"
                        multiple
                        chips
                        closable-chips
                        variant="outlined"
                        density="comfortable"
                        class="mb-3"
                        :disabled="saving"
                        data-test="template-webs"
                    />

                    <v-switch
                        v-if="kind === 'product'"
                        v-model="localItem.require_tlp_clear"
                        :label="t('public_web.templates.require_tlp_clear')"
                        :hint="t('public_web.templates.require_tlp_clear_hint')"
                        persistent-hint
                        color="primary"
                        density="comfortable"
                        class="mb-2"
                        :disabled="saving"
                        data-test="template-require-tlp"
                    />

                    <div class="d-flex align-center mb-1">
                        <span class="text-title-small">{{ t('public_web.templates.source') }}</span>
                        <v-spacer />
                        <v-menu location="bottom end">
                            <template #activator="{ props: menuProps }">
                                <v-btn
                                    v-bind="menuProps"
                                    variant="text"
                                    size="small"
                                    prepend-icon="mdi-content-copy"
                                    :disabled="saving"
                                    data-test="template-start-from"
                                >
                                    {{ t('public_web.templates.start_from') }}
                                </v-btn>
                            </template>
                            <v-list density="compact">
                                <v-list-item
                                    v-for="start in starts"
                                    :key="start.name"
                                    :title="start.title"
                                    data-test="template-start"
                                    @click="localItem.source = start.source"
                                />
                            </v-list>
                        </v-menu>
                    </div>
                    <CodeEditor
                        v-model="localItem.source"
                        :aria-label="t('public_web.templates.source')"
                        :disabled="saving"
                        min-height="22rem"
                        max-height="60vh"
                        :completions="{ kind, attrKeys }"
                        data-test="template-source"
                    />
                </v-form>

                <!-- What core found wrong with the template, with its line. -->
                <v-alert
                    v-if="saveError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    data-test="template-error"
                    @click:close="saveError = ''"
                >
                    {{ saveError }}
                </v-alert>

                <v-expansion-panels class="mt-4">
                    <v-expansion-panel :title="t('public_web.templates.help_title')">
                        <v-expansion-panel-text>
                            <p class="mb-2">
                                {{ kind === 'product' ? t('public_web.templates.help_product') : t('public_web.templates.help_item') }}
                            </p>
                            <ul class="template-help mb-2">
                                <li
                                    v-for="entry in contextHelp"
                                    :key="entry.name"
                                >
                                    <code>{{ entry.name }}</code> — {{ t(entry.description) }}
                                </li>
                            </ul>
                            <template v-if="attrKeys.length">
                                <p class="mb-1">{{ t('public_web.templates.help_attrs') }}</p>
                                <div class="d-flex flex-wrap ga-1">
                                    <code
                                        v-for="key in attrKeys"
                                        :key="key"
                                        data-test="template-attr-key"
                                        >{{ `item.attrs.${key}` }}</code
                                    >
                                </div>
                            </template>
                            <p class="mt-2 mb-0 text-medium-emphasis">{{ t('public_web.templates.help_more') }}</p>
                        </v-expansion-panel-text>
                    </v-expansion-panel>
                </v-expansion-panels>
            </v-card-text>
        </v-card>

        <UnsavedChangesDialog
            v-model="confirmVisible"
            @continue="continueEditing"
            @save="saveAndClose"
            @discard="discardAndClose"
        />
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import CodeEditor from '@/components/common/CodeEditor.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import UnsavedChangesDialog from '@/components/common/dialogs/UnsavedChangesDialog.vue'
    import { useAuth } from '@/composables/useAuth'
    import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
    import {
        createPublicWebTemplate,
        getAllProductPresets,
        getAllReportItemTypes,
        getBuiltinPublicWebTemplates,
        updatePublicWebTemplate
    } from '@/api/config'
    import type { PublicWebTemplate } from '@/types/public-web-template'

    type Kind = 'product' | 'item'

    type TypeOption = {
        id: number
        title: string
        attribute_groups?: Array<{ attribute_group_items?: Array<{ title?: string }> }>
    }

    const props = withDefaults(
        defineProps<{
            editItem?: PublicWebTemplate | null
            /** Every template, so the webs another template of the same target claims are not offered. */
            templates?: PublicWebTemplate[]
            /** The webs a template can be restricted to. */
            publicWebs?: Array<{ id: number; name: string }>
        }>(),
        { editItem: null, templates: () => [], publicWebs: () => [] }
    )

    const emit = defineEmits<{ (e: 'saved'): void }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const formRef = ref<{ validate: () => Promise<{ valid: boolean }>; reset: () => void } | null>(null)
    const dialog = ref(false)
    const saving = ref(false)
    const saveError = ref('')

    const emptyItem = (): PublicWebTemplate => ({
        id: null,
        name: '',
        product_preset_id: null,
        report_item_type_id: null,
        source: '',
        require_tlp_clear: true,
        public_web_ids: []
    })
    const localItem = ref<PublicWebTemplate>(emptyItem())
    const isEdit = computed(() => localItem.value.id != null)
    const canUpdate = computed(() => checkPermission('CONFIG_PUBLIC_WEB_NODE_UPDATE'))

    const kind = ref<Kind>('product')
    const kindItems = computed(() => [
        { title: t('public_web.templates.kind_product'), value: 'product' },
        { title: t('public_web.templates.kind_item'), value: 'item' }
    ])

    function setKind(value: Kind): void {
        kind.value = value
        localItem.value.product_preset_id = null
        localItem.value.report_item_type_id = null
    }

    // What the template is for: a product preset (its products' page) or a report item type, by kind.
    const target = computed<number | null>({
        get: () => (kind.value === 'product' ? localItem.value.product_preset_id : localItem.value.report_item_type_id),
        set: (value) => {
            if (kind.value === 'product') {
                localItem.value.product_preset_id = value
            } else {
                localItem.value.report_item_type_id = value
            }
        }
    })

    // -- types ---------------------------------------------------------------------

    const presets = ref<TypeOption[]>([])
    const reportItemTypes = ref<TypeOption[]>([])
    const loadingTypes = ref(false)

    // Loaded separately: the product presets need their own permission, and a refusal there
    // must not leave the report item types empty too.
    async function loadTypes(): Promise<void> {
        loadingTypes.value = true
        const [presetsResult, itemsResult] = await Promise.allSettled([
            getAllProductPresets({ search: '' }),
            getAllReportItemTypes({ search: '' })
        ])
        if (presetsResult.status === 'fulfilled') {
            const items = (presetsResult.value as { data?: { items?: Array<{ id: number; name: string }> } }).data?.items || []
            presets.value = items.map((preset) => ({ id: preset.id, title: preset.name }))
        } else {
            console.error('Error loading product presets for report templates:', presetsResult.reason)
        }
        if (itemsResult.status === 'fulfilled') {
            reportItemTypes.value = (itemsResult.value as { data?: { items?: TypeOption[] } }).data?.items || []
        } else {
            console.error('Error loading report item types for report templates:', itemsResult.reason)
        }
        loadingTypes.value = false
    }

    // Every product preset or type: one may have a template for every web and others for chosen webs.
    const targetItems = computed<TypeOption[]>(() => (kind.value === 'product' ? presets.value : reportItemTypes.value))

    // -- webs ------------------------------------------------------------------------

    // The other templates of the chosen product preset or type, which this one must not overlap.
    const siblings = computed<PublicWebTemplate[]>(() => {
        if (target.value == null) return []
        const field = kind.value === 'product' ? 'product_preset_id' : 'report_item_type_id'
        return props.templates.filter((template) => template.id !== localItem.value.id && template[field] === target.value)
    })

    function claimOf(webId: number): PublicWebTemplate | undefined {
        return siblings.value.find((template) => (template.public_web_ids || []).includes(webId))
    }

    // A web another template of the same target is for cannot be chosen; it says which template has it.
    function webItemProps(web: { id: number }): Record<string, unknown> {
        const claim = claimOf(web.id)
        return claim ? { disabled: true, subtitle: t('public_web.templates.web_taken', { name: claim.name }) } : {}
    }

    // None chosen means every web, which only one template of a target can be for.
    function everyWebRule(webIds: number[] | null): true | string {
        if (webIds && webIds.length) return true
        const everyWeb = siblings.value.find((template) => !(template.public_web_ids || []).length)
        return everyWeb ? t('public_web.templates.every_web_taken', { name: everyWeb.name }) : true
    }

    // The attrs names a template of the chosen report item type can use: the attribute
    // titles in snake_case, as presenter templates name them.
    const attrKeys = computed<string[]>(() => {
        if (kind.value !== 'item') return []
        const type = reportItemTypes.value.find((candidate) => candidate.id === localItem.value.report_item_type_id)
        const keys = (type?.attribute_groups || [])
            .flatMap((group) => group.attribute_group_items || [])
            .map((item) => (item.title || '').toLowerCase().replaceAll(' ', '_'))
            .filter(Boolean)
        return [...new Set(keys)]
    })

    // -- starting points -----------------------------------------------------------

    const builtins = ref<Record<string, string>>({})

    async function loadBuiltins(): Promise<void> {
        if (Object.keys(builtins.value).length) return
        try {
            const response = (await getBuiltinPublicWebTemplates()) as { data?: { items?: Array<{ name: string; source: string }> } }
            builtins.value = Object.fromEntries((response.data?.items || []).map((item) => [item.name, item.source]))
        } catch (error) {
            console.error('Error loading the built-in report templates:', error)
        }
    }

    const productSkeleton = (base: string, blocks: string): string =>
        `{% extends "${base}" %}\n\n` +
        '{#- Override only the blocks you need: header, items and links (the report page),\n' +
        '    summary (the homepage entry) and rss (the RSS text). -#}\n' +
        blocks

    const starts = computed(() =>
        kind.value === 'product'
            ? [
                  {
                      name: 'base',
                      title: t('public_web.templates.start_product_base'),
                      source: productSkeleton(
                          'builtin/product_base.html',
                          '{% block items %}\n' +
                              '    {%- for item in product.body_items %}\n' +
                              '        {%- if not selected_items or loop.index in selected_items %}\n' +
                              '            {{ render_item(item, loop.index) }}\n' +
                              '        {%- endif %}\n' +
                              '    {%- endfor %}\n' +
                              '{% endblock %}\n'
                      )
                  },
                  {
                      name: 'vulnerability',
                      title: t('public_web.templates.start_product_vulnerability'),
                      source: productSkeleton('builtin/product_vulnerability.html', '')
                  }
              ]
            : Object.entries(builtins.value)
                  .filter(([name]) => name.startsWith('builtin/item_'))
                  .map(([name, source]) => ({ name, title: name.replace('builtin/', ''), source }))
    )

    // -- help ------------------------------------------------------------------------

    const contextHelp = computed(() =>
        kind.value === 'product'
            ? [
                  { name: 'product', description: 'public_web.templates.help_ctx_product' },
                  { name: 'links', description: 'public_web.templates.help_ctx_links' },
                  { name: 'render_item(item, index)', description: 'public_web.templates.help_ctx_render_item' },
                  { name: 'selected_items', description: 'public_web.templates.help_ctx_selected_items' },
                  { name: 't(key)', description: 'public_web.templates.help_ctx_t' }
              ]
            : [
                  { name: 'item', description: 'public_web.templates.help_ctx_item' },
                  { name: 'index', description: 'public_web.templates.help_ctx_index' },
                  { name: 'product', description: 'public_web.templates.help_ctx_product' },
                  { name: 'links', description: 'public_web.templates.help_ctx_links' },
                  { name: 't(key)', description: 'public_web.templates.help_ctx_t' }
              ]
    )

    // -- saving ----------------------------------------------------------------------

    async function persist(): Promise<boolean> {
        saveError.value = ''
        const { valid } = (await formRef.value?.validate()) ?? { valid: false }
        if (!valid) return false
        saving.value = true
        try {
            const template = { ...localItem.value }
            if (kind.value === 'item') {
                template.require_tlp_clear = true
            }
            if (isEdit.value) {
                await updatePublicWebTemplate(template)
            } else {
                await createPublicWebTemplate({ ...template, id: -1 })
            }
            emit('saved')
            return true
        } catch (error) {
            // Core says what is wrong with the template (and on which line), so show it here.
            const data = (error as { response?: { data?: { error?: string } } })?.response?.data
            saveError.value = data?.error || t('common.error_saving')
            return false
        } finally {
            saving.value = false
        }
    }

    function closeDialog(): void {
        formRef.value?.reset()
        localItem.value = emptyItem()
        kind.value = 'product'
        saveError.value = ''
        dialog.value = false
    }

    const { confirmVisible, capture, requestClose, continueEditing, saveAndClose, discardAndClose } = useUnsavedChanges({
        getState: () => ({ item: localItem.value, kind: kind.value }),
        save: persist,
        close: closeDialog
    })

    watch(
        () => props.editItem,
        (item) => {
            if (item && item.id != null) {
                localItem.value = { ...emptyItem(), ...item, public_web_ids: [...(item.public_web_ids || [])] }
                kind.value = item.product_preset_id != null ? 'product' : 'item'
                dialog.value = true
            }
        },
        { immediate: true }
    )

    watch(dialog, (open) => {
        if (open) {
            loadTypes()
            loadBuiltins()
            capture()
        } else {
            saving.value = false
            saveError.value = ''
        }
    })
</script>

<style scoped>
    .template-help {
        padding-inline-start: 1.25rem;
    }
</style>
