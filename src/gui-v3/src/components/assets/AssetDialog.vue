<template>
    <v-dialog
        v-model="open"
        max-width="900"
        persistent
        scrollable
    >
        <v-card>
            <DialogToolbar
                :title="t(editing ? 'asset.edit' : 'asset.add_new')"
                :saving="saving"
                :save-disabled="!canModify"
                @cancel="close"
                @save="save"
            />

            <v-tabs
                v-if="editing"
                v-model="tab"
                color="primary"
            >
                <v-tab value="details">{{ t('common.details') }}</v-tab>
                <v-tab value="vulnerabilities">
                    {{ t('asset.vulnerabilities') }}
                    <v-badge
                        class="ml-3"
                        :content="unsolvedCount"
                        :color="unsolvedCount ? 'error' : 'success'"
                        inline
                    />
                </v-tab>
            </v-tabs>

            <v-card-text>
                <v-window v-model="tab">
                    <v-window-item value="details">
                        <v-form
                            ref="formRef"
                            @submit.prevent="save"
                        >
                            <v-text-field
                                v-model="form.name"
                                :label="t('asset.name')"
                                :rules="[required]"
                                :disabled="saving || !canModify"
                                variant="outlined"
                                class="mb-2"
                            />
                            <v-text-field
                                v-model="form.serial"
                                :label="t('asset.serial')"
                                :disabled="saving || !canModify"
                                variant="outlined"
                                class="mb-2"
                            />
                            <v-textarea
                                v-model="form.description"
                                :label="t('asset.description')"
                                :disabled="saving || !canModify"
                                variant="outlined"
                                rows="3"
                                class="mb-2"
                            />
                            <CpeEditor
                                v-model="cpeEntries"
                                :disabled="saving || !canModify"
                            />
                        </v-form>
                    </v-window-item>

                    <v-window-item value="vulnerabilities">
                        <v-alert
                            v-if="vulnerabilities.length === 0"
                            type="success"
                            variant="tonal"
                        >
                            {{ t('asset.no_vulnerabilities') }}
                        </v-alert>
                        <v-expansion-panels
                            v-else
                            variant="accordion"
                        >
                            <v-expansion-panel
                                v-for="vulnerability in vulnerabilities"
                                :key="vulnerability.report_item.id"
                            >
                                <v-expansion-panel-title>
                                    <div class="d-flex align-center w-100 pr-4">
                                        <v-icon
                                            :color="vulnerability.solved ? 'success' : 'error'"
                                            class="mr-3"
                                        >
                                            {{ vulnerability.solved ? 'mdi-shield-check' : 'mdi-shield-alert' }}
                                        </v-icon>
                                        <span>{{ vulnerability.report_item.title }}</span>
                                        <v-spacer />
                                        <v-switch
                                            :model-value="vulnerability.solved"
                                            :label="t('asset.solved')"
                                            :disabled="savingVulnerability === vulnerability.report_item.id || !canModify"
                                            color="success"
                                            hide-details
                                            @click.stop
                                            @update:model-value="setSolved(vulnerability, Boolean($event))"
                                        />
                                    </div>
                                </v-expansion-panel-title>
                                <v-expansion-panel-text>
                                    <VulnerabilityDetail :report-item="vulnerability.report_item" />
                                </v-expansion-panel-text>
                            </v-expansion-panel>
                        </v-expansion-panels>
                    </v-window-item>
                </v-window>

                <v-alert
                    v-if="error"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="error = false"
                >
                    {{ t('asset.error') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import { createNewAsset, solveVulnerability, updateAsset } from '@/api/assets'
    import CpeEditor, { type CpeEntry } from './CpeEditor.vue'
    import VulnerabilityDetail from './VulnerabilityDetail.vue'
    import type { Asset, AssetVulnerability } from '@/types/assets'

    const props = defineProps<{ modelValue: boolean; asset?: Asset | null; groupId: string }>()
    const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>()
    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
    const editing = computed(() => Boolean(props.asset?.id))
    const canModify = computed(() => checkPermission('MY_ASSETS_CREATE'))
    const tab = ref<'details' | 'vulnerabilities'>('details')
    const saving = ref(false)
    const savingVulnerability = ref<number | null>(null)
    const error = ref(false)
    const formRef = ref<{ validate?: () => Promise<{ valid: boolean }> } | null>(null)
    const form = ref({ name: '', serial: '', description: '' })
    const cpeEntries = ref<CpeEntry[]>([])
    const vulnerabilities = ref<AssetVulnerability[]>([])

    const unsolvedCount = computed(() => vulnerabilities.value.filter((item) => !item.solved).length)
    const required = (value: string): true | string => Boolean(value?.trim()) || t('error.required')
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }

    watch(
        () => [props.modelValue, props.asset] as const,
        ([visible, asset]) => {
            if (!visible) return
            form.value = { name: asset?.name || '', serial: asset?.serial || '', description: asset?.description || '' }
            cpeEntries.value = (asset?.asset_cpes || []).map((item) => ({ value: item.value.replaceAll('%', '*') }))
            vulnerabilities.value = (asset?.vulnerabilities || []).map((item) => ({ ...item }))
            tab.value = 'details'
            error.value = false
        },
        { immediate: true, deep: true }
    )

    const save = async (): Promise<void> => {
        if (!canModify.value) return
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return
        saving.value = true
        error.value = false
        const payload: Asset = {
            id: props.asset?.id || 0,
            asset_group_id: props.groupId,
            ...form.value,
            asset_cpes: cpeEntries.value.map((entry) => ({ value: entry.value.replaceAll('*', '%') }))
        }
        try {
            if (editing.value) await updateAsset(payload)
            else await createNewAsset(payload)
            notify('success', editing.value ? 'asset.successful_edit' : 'asset.successful')
            emit('saved')
            open.value = false
        } catch {
            error.value = true
            notify('error', 'asset.error')
        } finally {
            saving.value = false
        }
    }

    const setSolved = async (vulnerability: AssetVulnerability, solved: boolean): Promise<void> => {
        if (!props.asset?.id || !canModify.value) return
        savingVulnerability.value = vulnerability.report_item.id
        try {
            await solveVulnerability({
                group_id: props.groupId,
                asset_id: props.asset.id,
                vulnerability_id: vulnerability.report_item.id,
                solved
            })
            vulnerability.solved = solved
            notify('success', 'asset.vulnerability_updated')
            emit('saved')
        } catch {
            notify('error', 'asset.vulnerability_update_error')
        } finally {
            savingVulnerability.value = null
        }
    }

    const close = (): void => {
        open.value = false
    }
</script>
