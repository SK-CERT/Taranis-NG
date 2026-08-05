<template>
    <AttributeItemLayout
        :add-button="false"
        :values="values"
    >
        <template #content>
            <div class="attachment-list">
                <button
                    v-if="canAddAttachment"
                    type="button"
                    class="attachment-dropzone"
                    :class="{ 'attachment-dropzone--active': dragActive }"
                    :disabled="uploading"
                    @click="openFilePicker"
                    @dragenter.prevent="dragActive = true"
                    @dragover.prevent="dragActive = true"
                    @dragleave.prevent="dragActive = false"
                    @drop.prevent="handleDrop"
                >
                    <v-icon size="28">mdi-cloud-upload-outline</v-icon>
                    <span>{{ t('drop_zone.default_message') }}</span>
                </button>
                <input
                    ref="fileInput"
                    class="attachment-file-input"
                    type="file"
                    multiple
                    :disabled="!canAddAttachment || uploading"
                    @change="handleFileInput"
                />

                <v-alert
                    v-if="operationError"
                    type="error"
                    variant="tonal"
                    density="compact"
                    closable
                    class="mb-2"
                    @click:close="operationError = false"
                >
                    {{ t('error.server_error') }}
                </v-alert>

                <div
                    v-for="(value, index) in values"
                    :key="attachmentKey(value, index)"
                    class="attachment-row"
                    :class="{ 'attachment-row--remote': value.remote }"
                >
                    <v-icon
                        color="primary"
                        class="attachment-row__icon"
                    >
                        {{ ICONS.FILE_DOCUMENT }}
                    </v-icon>

                    <button
                        type="button"
                        class="attachment-row__details"
                        :disabled="value.uploading"
                        @click="openDetails(value)"
                    >
                        <span class="attachment-row__name">{{ attachmentName(value) }}</span>
                        <span
                            v-if="value.binary_description"
                            class="attachment-row__description"
                        >
                            {{ value.binary_description }}
                        </span>
                        <span class="attachment-row__meta">
                            {{ value.binary_mime_type || value.file?.type || 'application/octet-stream' }}
                            <template v-if="attachmentSize(value) > 0"> · {{ formatFileSize(attachmentSize(value)) }}</template>
                            <template v-if="value.last_updated"> · {{ t('drop_zone.last_updated') }} {{ value.last_updated }}</template>
                            <template v-if="value.user?.name"> · {{ value.user.name }}</template>
                        </span>
                    </button>

                    <v-progress-circular
                        v-if="value.uploading"
                        indeterminate
                        color="primary"
                        size="22"
                        width="2"
                    />
                    <v-btn
                        v-else-if="value.uploadError && value.file"
                        variant="text"
                        size="small"
                        color="error"
                        :title="t('attribute.add_attachment')"
                        @click="uploadValue(value)"
                    >
                        <v-icon>mdi-reload</v-icon>
                    </v-btn>
                    <v-btn
                        v-if="canDownload(value)"
                        variant="text"
                        size="small"
                        :title="t('drop_zone.download')"
                        @click="downloadAttachmentNow(value)"
                    >
                        <v-icon>{{ ICONS.DOWNLOAD }}</v-icon>
                    </v-btn>
                    <v-btn
                        v-if="canManageValue(value)"
                        variant="text"
                        size="small"
                        :title="t('common.edit')"
                        @click="openDescriptionEditor(value)"
                    >
                        <v-icon>mdi-pencil-outline</v-icon>
                    </v-btn>
                    <v-btn
                        v-if="canManageValue(value)"
                        variant="text"
                        size="small"
                        color="error"
                        :title="t('common.delete')"
                        @click="requestDelete(value)"
                    >
                        <v-icon>mdi-delete-outline</v-icon>
                    </v-btn>
                </div>
            </div>
        </template>
    </AttributeItemLayout>

    <v-dialog
        v-model="descriptionDialog"
        max-width="620px"
        persistent
    >
        <v-card>
            <v-card-title class="d-flex align-center">
                <v-icon
                    color="primary"
                    class="mr-2"
                >
                    {{ ICONS.FILE_DOCUMENT }}
                </v-icon>
                {{ descriptionMode === 'new' ? t('drop_zone.attachment_load') : t('drop_zone.attachment_detail') }}
            </v-card-title>
            <v-card-text>
                <div class="text-body-2 font-weight-medium mb-3">
                    {{ descriptionMode === 'new' ? currentPendingFile?.name : attachmentName(selectedValue) }}
                </div>
                <v-textarea
                    v-model="descriptionDraft"
                    :label="t('drop_zone.file_description')"
                    rows="3"
                    auto-grow
                    autofocus
                    :readonly="descriptionMode === 'detail'"
                />
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    variant="text"
                    @click="cancelDescriptionDialog"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    v-if="descriptionMode !== 'detail'"
                    color="primary"
                    variant="elevated"
                    :loading="savingDescription"
                    @click="confirmDescription"
                >
                    {{ t('common.save') }}
                </v-btn>
                <v-btn
                    v-else
                    color="primary"
                    variant="text"
                    @click="descriptionDialog = false"
                >
                    {{ t('common.done') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <ConfirmationDialog
        v-model="deleteDialog"
        @confirm="deleteSelectedAttachment"
    >
        {{ attachmentName(selectedValue) }}
    </ConfirmationDialog>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import AuthService from '@/services/auth_service'
    import Permissions from '@/services/auth/permissions'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import { useAttributes } from './useAttributes'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import { downloadAttachment, removeAttachment, updateAttachmentDescription, uploadAttachment } from '@/api/analyze'

    type AttachmentValue = {
        id?: number
        index?: string | number
        value?: string
        remote?: boolean
        locked?: boolean
        binary_description?: string
        binary_mime_type?: string
        binary_size?: number
        last_updated?: string
        user?: { name?: string } | null
        file?: File
        uploading?: boolean
        uploadError?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = {
        id?: number
        max_occurrence?: number | null
        [key: string]: unknown
    }

    type DescriptionMode = 'new' | 'edit' | 'detail'
    type FileInputControl = {
        click: () => void
        files: ArrayLike<File> | null
        value: string
    }

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttachmentValue[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number | null
        }>(),
        {
            readOnly: false,
            edit: false,
            modify: false
        }
    )

    const { t } = useI18n()
    // Besides the field-editing helpers, this composable keeps the values synchronized when
    // another analyst uploads, updates, or deletes an attachment over SSE.
    useAttributes(props)
    const fileInput = ref<FileInputControl | null>(null)
    const dragActive = ref(false)
    const operationError = ref(false)
    const pendingFiles = ref<File[]>([])
    const currentPendingFile = ref<File | null>(null)
    const selectedValue = ref<AttachmentValue | null>(null)
    const descriptionDraft = ref('')
    const descriptionDialog = ref(false)
    const descriptionMode = ref<DescriptionMode>('detail')
    const savingDescription = ref(false)
    const deleteDialog = ref(false)
    let temporaryId = -1

    const mayCreate = computed(() => AuthService.hasPermission(Permissions.ANALYZE_CREATE))
    const mayUpdate = computed(() => AuthService.hasPermission(Permissions.ANALYZE_UPDATE) && props.modify === true)
    const canManage = computed(() => !props.readOnly && (props.edit ? mayUpdate.value : mayCreate.value))
    const uploading = computed(() => props.values.some((value) => value.uploading))
    const canAddAttachment = computed(() => {
        const maximum = props.attributeGroup.max_occurrence ?? Infinity
        const describing = currentPendingFile.value ? 1 : 0
        return canManage.value && props.values.length + pendingFiles.value.length + describing < maximum
    })

    const attachmentKey = (value: AttachmentValue, index: number): string => String(value.id ?? value.index ?? index)
    const attachmentName = (value: AttachmentValue | null): string => value?.value || value?.file?.name || t('attribute.select_attachment')
    const attachmentSize = (value: AttachmentValue): number => Number(value.binary_size ?? value.file?.size ?? 0)

    const formatFileSize = (bytes: number): string => {
        if (!bytes) return '0 B'
        const units = ['B', 'KB', 'MB', 'GB', 'TB']
        const unit = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
        return `${parseFloat((bytes / Math.pow(1024, unit)).toFixed(2))} ${units[unit]}`
    }

    const openFilePicker = (): void => fileInput.value?.click()

    const acceptFiles = (files: File[]): void => {
        if (!canAddAttachment.value || files.length === 0) return
        const maximum = props.attributeGroup.max_occurrence ?? Infinity
        const describing = currentPendingFile.value ? 1 : 0
        const available = Math.max(0, maximum - props.values.length - pendingFiles.value.length - describing)
        pendingFiles.value.push(...files.slice(0, available))
        openNextFileDescription()
    }

    const handleFileInput = (event: Event): void => {
        const input = event.target as unknown as FileInputControl
        acceptFiles(Array.from(input.files ?? []))
        input.value = ''
    }

    const handleDrop = (event: DragEvent): void => {
        dragActive.value = false
        acceptFiles(Array.from(event.dataTransfer?.files ?? []))
    }

    const openNextFileDescription = (): void => {
        if (descriptionDialog.value || currentPendingFile.value || pendingFiles.value.length === 0) return
        currentPendingFile.value = pendingFiles.value.shift() ?? null
        descriptionDraft.value = ''
        descriptionMode.value = 'new'
        descriptionDialog.value = currentPendingFile.value !== null
    }

    const queueAttachment = (file: File, description: string): AttachmentValue => {
        const value: AttachmentValue = {
            id: temporaryId--,
            index: props.values.length,
            value: file.name,
            binary_description: description,
            binary_mime_type: file.type || 'application/octet-stream',
            binary_size: file.size,
            user: null,
            remote: false,
            file
        }
        props.values.push(value)
        return value
    }

    const uploadValue = async (value: AttachmentValue): Promise<boolean> => {
        if (!value.file || !props.reportItemId || !props.attributeGroup.id) return false
        value.uploading = true
        value.uploadError = false
        operationError.value = false
        try {
            const response = await uploadAttachment(props.reportItemId, props.attributeGroup.id, value.file, value.binary_description || '')
            value.id = Number(response.data.attribute_id)
            value.index = props.values.indexOf(value)
            delete value.file
            value.uploading = false
            return true
        } catch (error) {
            console.error('Failed to upload attachment:', error)
            value.uploading = false
            value.uploadError = true
            operationError.value = true
            return false
        }
    }

    const confirmDescription = async (): Promise<void> => {
        if (descriptionMode.value === 'new' && currentPendingFile.value) {
            const value = queueAttachment(currentPendingFile.value, descriptionDraft.value)
            currentPendingFile.value = null
            descriptionDialog.value = false
            if (props.edit) await uploadValue(value)
            openNextFileDescription()
            return
        }

        if (descriptionMode.value === 'edit' && selectedValue.value) {
            savingDescription.value = true
            operationError.value = false
            try {
                if (props.edit && props.reportItemId && selectedValue.value.id && selectedValue.value.id > 0) {
                    const response = await updateAttachmentDescription({
                        report_item_id: props.reportItemId,
                        attribute_id: selectedValue.value.id,
                        description: descriptionDraft.value
                    })
                    selectedValue.value.binary_description = response.data.binary_description ?? descriptionDraft.value
                    selectedValue.value.uploadError = false
                } else {
                    selectedValue.value.binary_description = descriptionDraft.value
                }
                descriptionDialog.value = false
            } catch (error) {
                console.error('Failed to update attachment description:', error)
                operationError.value = true
            } finally {
                savingDescription.value = false
            }
        }
    }

    const cancelDescriptionDialog = (): void => {
        const wasNew = descriptionMode.value === 'new'
        currentPendingFile.value = null
        descriptionDialog.value = false
        if (wasNew) openNextFileDescription()
    }

    const canDownload = (value: AttachmentValue): boolean => !!props.reportItemId && !!value.id && value.id > 0 && !value.uploading
    const canManageValue = (value: AttachmentValue): boolean => canManage.value && !value.remote && !value.locked && !value.uploading

    const downloadAttachmentNow = (value: AttachmentValue): void => {
        if (!canDownload(value)) return
        downloadAttachment(`/analyze/report-items/${props.reportItemId}/file-attributes/${value.id}/file`, attachmentName(value))
    }

    const openDescriptionEditor = (value: AttachmentValue): void => {
        selectedValue.value = value
        descriptionDraft.value = value.binary_description || ''
        descriptionMode.value = 'edit'
        descriptionDialog.value = true
    }

    const openDetails = (value: AttachmentValue): void => {
        if (canManageValue(value)) {
            openDescriptionEditor(value)
            return
        }
        selectedValue.value = value
        descriptionDraft.value = value.binary_description || ''
        descriptionMode.value = 'detail'
        descriptionDialog.value = true
    }

    const requestDelete = (value: AttachmentValue): void => {
        selectedValue.value = value
        deleteDialog.value = true
    }

    const deleteSelectedAttachment = async (): Promise<void> => {
        const value = selectedValue.value
        if (!value) return
        operationError.value = false
        try {
            if (props.edit && props.reportItemId && value.id && value.id > 0) {
                await removeAttachment({ report_item_id: props.reportItemId, attribute_id: value.id })
            }
            const index = props.values.indexOf(value)
            if (index >= 0) props.values.splice(index, 1)
            props.values.forEach((item, itemIndex) => (item.index = itemIndex))
            selectedValue.value = null
        } catch (error) {
            console.error('Failed to delete attachment:', error)
            operationError.value = true
        }
    }
</script>

<style scoped>
    .attachment-list {
        display: flex;
        flex-direction: column;
        gap: 1px;
        width: 100%;
        overflow: hidden;
        border: 1px solid rgba(var(--v-border-color), 0.5);
        border-radius: 6px;
    }

    .attachment-file-input {
        display: none;
    }

    .attachment-dropzone {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        min-height: 68px;
        padding: 12px;
        color: rgb(var(--v-theme-primary));
        background: rgba(var(--v-theme-primary), 0.05);
        border: 1px dashed rgba(var(--v-theme-primary), 0.55);
        cursor: pointer;
        transition:
            background-color 120ms ease,
            border-color 120ms ease;
    }

    .attachment-dropzone:hover,
    .attachment-dropzone:focus-visible,
    .attachment-dropzone--active {
        background: rgba(var(--v-theme-primary), 0.12);
        border-color: rgb(var(--v-theme-primary));
        outline: none;
    }

    .attachment-row {
        display: flex;
        align-items: center;
        gap: 4px;
        min-height: 58px;
        padding: 7px 8px 7px 12px;
        background: rgb(var(--v-theme-surface));
        border-top: 1px solid rgba(var(--v-border-color), 0.35);
    }

    .attachment-row--remote {
        background: rgba(var(--v-theme-primary), 0.035);
    }

    .attachment-row__icon {
        flex: 0 0 auto;
        margin-right: 6px;
    }

    .attachment-row__details {
        display: flex;
        flex: 1 1 auto;
        flex-direction: column;
        min-width: 0;
        padding: 3px 6px;
        color: inherit;
        text-align: left;
        background: transparent;
        border: 0;
        cursor: pointer;
    }

    .attachment-row__details:focus-visible {
        border-radius: 3px;
        outline: 2px solid rgb(var(--v-theme-primary));
    }

    .attachment-row__name,
    .attachment-row__description,
    .attachment-row__meta {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .attachment-row__name {
        font-size: 0.9rem;
        font-weight: 600;
    }

    .attachment-row__description,
    .attachment-row__meta {
        color: rgba(var(--v-theme-on-surface), 0.66);
        font-size: 0.75rem;
    }
</style>
