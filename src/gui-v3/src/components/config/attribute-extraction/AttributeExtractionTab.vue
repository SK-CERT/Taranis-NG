<template>
    <v-container fluid>
        <v-alert
            v-if="!extractionEnabled"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
        >
            {{ t('attribute_extraction.disabled_hint') }}
        </v-alert>

        <EditableEntityTable
            v-model="rows"
            server
            :items="rows"
            :title="t('attribute_extraction.title')"
            :headers="headers"
            :default-item="defaultRule"
            :add-title="t('attribute_extraction.add')"
            :edit-title="t('attribute_extraction.edit')"
            :allow-add="canCreate"
            :allow-edit="canUpdate"
            :allow-delete="canDelete"
            :loading="loading"
            :saving="saving"
            dialog-max-width="800"
            searchable
            :no-data-text="t('attribute_extraction.none')"
            @save="onSave"
            @delete="onDelete"
        >
            <template #item.enabled="{ item }">
                <v-icon
                    :icon="asRule(item).enabled ? 'mdi-check-circle' : 'mdi-minus-circle-outline'"
                    :color="asRule(item).enabled ? 'success' : 'disabled'"
                    size="small"
                />
            </template>

            <template #item.pattern="{ item }">
                <code class="pattern-cell">{{ asRule(item).pattern }}</code>
            </template>

            <template #item.osint_source_groups="{ item }">
                <span v-if="!asRule(item).osint_source_groups?.length">{{ t('attribute_extraction.all_sources') }}</span>
                <v-chip
                    v-for="groupId in asRule(item).osint_source_groups"
                    v-else
                    :key="groupId"
                    size="x-small"
                    class="me-1"
                >
                    {{ groupName(groupId) }}
                </v-chip>
            </template>

            <template #form="{ item }">
                <v-text-field
                    v-model="asRule(item).name"
                    :label="t('attribute_extraction.name')"
                    variant="outlined"
                    density="comfortable"
                    :rules="[requiredRule]"
                />
                <v-text-field
                    v-model="asRule(item).attribute_key"
                    :label="t('attribute_extraction.attribute_key')"
                    :hint="t('attribute_extraction.attribute_key_hint')"
                    persistent-hint
                    variant="outlined"
                    density="comfortable"
                    class="mb-3"
                    :rules="[requiredRule]"
                />
                <v-text-field
                    v-model="asRule(item).pattern"
                    :label="t('attribute_extraction.pattern')"
                    :hint="t('attribute_extraction.pattern_hint')"
                    persistent-hint
                    variant="outlined"
                    density="comfortable"
                    class="mb-3 pattern-field"
                    :rules="[requiredRule, patternRule]"
                />
                <v-row>
                    <v-col cols="6">
                        <v-text-field
                            v-model.number="asRule(item).capture_group"
                            type="number"
                            min="0"
                            :label="t('attribute_extraction.capture_group')"
                            :hint="t('attribute_extraction.capture_group_hint')"
                            persistent-hint
                            variant="outlined"
                            density="comfortable"
                        />
                    </v-col>
                    <v-col cols="6">
                        <v-text-field
                            v-model.number="asRule(item).max_matches"
                            type="number"
                            min="1"
                            :label="t('attribute_extraction.max_matches')"
                            :hint="t('attribute_extraction.max_matches_hint')"
                            persistent-hint
                            variant="outlined"
                            density="comfortable"
                        />
                    </v-col>
                </v-row>
                <v-autocomplete
                    v-model="asRule(item).osint_source_groups"
                    :items="groupOptions"
                    item-title="title"
                    item-value="value"
                    :label="t('attribute_extraction.source_groups')"
                    :hint="t('attribute_extraction.source_groups_hint')"
                    persistent-hint
                    multiple
                    chips
                    closable-chips
                    variant="outlined"
                    density="comfortable"
                    class="mt-3"
                    :return-object="false"
                />
                <v-textarea
                    v-model="asRule(item).description"
                    :label="t('attribute_extraction.description')"
                    variant="outlined"
                    density="comfortable"
                    rows="2"
                    class="mt-3"
                />
                <v-switch
                    v-model="asRule(item).enabled"
                    :label="t('attribute_extraction.enabled')"
                    color="primary"
                    density="compact"
                    hide-details
                />
            </template>
        </EditableEntityTable>

        <v-alert
            v-if="errorMessage"
            type="error"
            density="compact"
            class="mt-4"
        >
            {{ errorMessage }}
        </v-alert>
    </v-container>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useConfigStore } from '@/stores/config'
    import { useSettingsStore } from '@/stores/settings'
    import { Settings } from '@/types/settings'
    import { createNewAttributeExtractionRule, deleteAttributeExtractionRule, updateAttributeExtractionRule } from '@/api/config'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'
    import { useAuth } from '@/composables/useAuth'

    type GroupRef = { id: string }

    type ExtractionRule = {
        id?: number
        name: string
        attribute_key: string
        pattern: string
        description: string
        enabled: boolean
        capture_group: number
        max_matches: number
        osint_source_groups: string[]
        [key: string]: unknown
    }

    const { t } = useI18n()
    const configStore = useConfigStore()
    const settingsStore = useSettingsStore()
    const { checkPermission } = useAuth()

    const canCreate = computed(() => checkPermission('CONFIG_ATTRIBUTE_EXTRACTION_CREATE'))
    const canUpdate = computed(() => checkPermission('CONFIG_ATTRIBUTE_EXTRACTION_UPDATE'))
    const canDelete = computed(() => checkPermission('CONFIG_ATTRIBUTE_EXTRACTION_DELETE'))

    const rows = ref<ExtractionRule[]>([])
    const loading = ref(false)
    const saving = ref(false)
    const errorMessage = ref('')

    const headers = [
        { title: t('attribute_extraction.enabled'), key: 'enabled', sortable: false, width: '90px' },
        { title: t('attribute_extraction.name'), key: 'name' },
        { title: t('attribute_extraction.attribute_key'), key: 'attribute_key' },
        { title: t('attribute_extraction.pattern'), key: 'pattern', sortable: false },
        { title: t('attribute_extraction.source_groups'), key: 'osint_source_groups', sortable: false },
        { title: t('settings.actions'), key: 'actions', sortable: false, width: '110px' }
    ]

    const asRule = (item: unknown): ExtractionRule => item as ExtractionRule

    const defaultRule = (): ExtractionRule => ({
        name: '',
        attribute_key: '',
        pattern: '',
        description: '',
        enabled: true,
        capture_group: 0,
        max_matches: 100,
        osint_source_groups: []
    })

    const groupOptions = computed(() =>
        (configStore.osintSourceGroups?.items ?? []).map((group: Record<string, unknown>) => ({
            title: String(group['name'] ?? group['id']),
            value: String(group['id'])
        }))
    )

    const groupName = (id: string): string => groupOptions.value.find((option) => option.value === id)?.title ?? id

    // The global switch lives in Settings; surfaced here so it is visible where the rules are.
    const extractionEnabled = computed(() => settingsStore.getSetting(Settings.ATTRIBUTE_EXTRACTION_ENABLED, 'true') !== 'false')

    const requiredRule = (value: unknown): boolean | string => (value ? true : t('attribute_extraction.required'))

    // Validated in the browser as well as on the server: catching a typo before the round
    // trip is the difference between an inline error and a 400.
    const patternRule = (value: unknown): boolean | string => {
        if (!value) return true
        try {
            new RegExp(String(value))
            return true
        } catch (error) {
            return t('attribute_extraction.invalid_pattern', { error: (error as Error).message })
        }
    }

    const loadData = async (): Promise<void> => {
        loading.value = true
        errorMessage.value = ''
        try {
            await configStore.loadAttributeExtractionRules({ search: '' })
            rows.value = ((configStore.attributeExtractionRules?.items ?? []) as Record<string, unknown>[]).map(fromApi)
            await configStore.loadOSINTSourceGroups({ search: '' })
        } catch (error) {
            errorMessage.value = String(error)
        } finally {
            loading.value = false
        }
    }

    // The component works in plain group ids; the API speaks objects.
    const toPayload = (rule: ExtractionRule): Record<string, unknown> => ({
        ...rule,
        osint_source_groups: (rule.osint_source_groups ?? []).map((id) => ({ id }))
    })

    const fromApi = (rule: Record<string, unknown>): ExtractionRule => ({
        ...(rule as unknown as ExtractionRule),
        osint_source_groups: ((rule['osint_source_groups'] as GroupRef[] | undefined) ?? []).map((group) => String(group.id))
    })

    const onSave = async (item: ExtractionRule, { isNew }: { isNew: boolean }): Promise<void> => {
        saving.value = true
        errorMessage.value = ''
        try {
            const payload = toPayload(item)
            if (isNew) {
                await createNewAttributeExtractionRule(payload)
            } else {
                await updateAttributeExtractionRule(payload)
            }
            await loadData()
        } catch (error) {
            errorMessage.value = String(error)
        } finally {
            saving.value = false
        }
    }

    const onDelete = async (item: ExtractionRule): Promise<void> => {
        errorMessage.value = ''
        try {
            await deleteAttributeExtractionRule(item)
            await loadData()
        } catch (error) {
            errorMessage.value = String(error)
        }
    }

    onMounted(loadData)
</script>

<style scoped>
    .pattern-cell {
        font-size: 0.8rem;
        word-break: break-all;
    }
    .pattern-field :deep(input) {
        font-family: monospace;
    }
</style>
