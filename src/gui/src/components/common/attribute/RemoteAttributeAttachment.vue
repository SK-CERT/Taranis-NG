<template>
    <div class="remote-attachments">
        <div
            v-for="value in attributeGroup.attributes"
            :key="value.id"
            class="remote-attachment"
        >
            <v-icon>{{ ICONS.FILE_DOCUMENT }}</v-icon>
            <div class="remote-attachment__details">
                <strong
                    ><bdi dir="auto">{{ value.value }}</bdi></strong
                >
                <span class="remote-attachment__meta text-medium-emphasis">
                    <bdi dir="ltr">{{ formatFileSize(value.binary_size) }}</bdi>
                    <bdi
                        v-if="value.binary_description"
                        dir="auto"
                        >{{ value.binary_description }}</bdi
                    >
                </span>
            </div>
            <v-btn
                icon="mdi-download"
                variant="text"
                color="primary"
                :title="t('common.download')"
                @click="download(value)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import { downloadReportItemAttachment } from '@/api/analyze'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'

    const { t } = useI18n()
    const { formatFileSize } = useLocaleFormatters()

    type RemoteAttachmentValue = {
        id: number | string
        value?: string
        binary_size?: number | null
        binary_description?: string | null
    }

    const props = defineProps<{
        attributeGroup: { attributes: RemoteAttachmentValue[] }
        reportItemId: number
    }>()

    const download = async (attachment: RemoteAttachmentValue): Promise<void> => {
        try {
            await downloadReportItemAttachment(props.reportItemId, attachment.id, attachment.value || 'attachment')
        } catch {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.server_error') }
                })
            )
        }
    }
</script>

<style scoped>
    .remote-attachments {
        display: grid;
        gap: 0.5rem;
    }

    .remote-attachment {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        gap: 0.75rem;
    }

    .remote-attachment + .remote-attachment {
        padding-top: 0.5rem;
        border-top: 1px solid rgba(var(--v-theme-outline), 0.2);
    }

    .remote-attachment__details {
        display: grid;
        min-width: 0;
        overflow-wrap: anywhere;
    }

    .remote-attachment__meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.15rem 0.6rem;
        align-items: baseline;
    }
</style>
