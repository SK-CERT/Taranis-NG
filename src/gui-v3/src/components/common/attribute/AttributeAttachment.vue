<template>
    <AttributeItemLayout
        :add-button="false"
        :values="values"
        @add-value="add"
    >
        <template #content>
            <div
                v-for="(value, index) in values"
                :key="`${value.index}-${index}`"
                class="value-holder"
            >
                <!-- Read-only or remote -->
                <div
                    v-if="readOnly || value.remote"
                    class="attachment-display d-flex align-center pa-3"
                >
                    <v-icon
                        color="primary"
                        class="mr-3"
                    >
                        {{ ICONS.FILE_DOCUMENT }}
                    </v-icon>
                    <div class="flex-grow-1">
                        <div class="text-body-2 font-weight-medium">
                            {{ value.binary_description || 'Attachment' }}
                        </div>
                        <div class="text-caption text-grey">{{ value.binary_mime_type }} - {{ formatFileSize(value.binary_size) }}</div>
                    </div>
                    <v-btn
                        size="small"
                        variant="text"
                        @click="downloadAttachmentNow(value)"
                    >
                        <v-icon>{{ ICONS.DOWNLOAD }}</v-icon>
                    </v-btn>
                </div>

                <!-- Editable -->
                <AttributeValueLayout
                    v-if="!readOnly && canModify && !value.remote"
                    :del-button="false"
                    :occurrence="attributeGroup.min_occurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="del(index)"
                >
                    <template #col_middle>
                        <div class="d-flex align-center">
                            <div
                                v-if="value.binary_description"
                                class="mr-3"
                            >
                                <div class="text-body-2">
                                    {{ value.binary_description }}
                                </div>
                                <div class="text-caption text-grey">
                                    {{ value.binary_mime_type }} - {{ formatFileSize(value.binary_size) }}
                                </div>
                            </div>
                            <v-btn
                                v-if="(value.id ?? 0) > 0"
                                size="small"
                                variant="text"
                                @click="downloadAttachmentNow(value)"
                            >
                                <v-icon>{{ ICONS.DOWNLOAD }}</v-icon>
                            </v-btn>
                        </div>
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { ICONS } from '@/config/ui-constants'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { useAttributes } from './useAttributes'
    import { downloadAttachment } from '@/api/analyze'

    type AttributeValueItem = {
        id?: number
        index?: string | number
        remote?: boolean
        locked?: boolean
        binary_description?: string
        binary_mime_type?: string
        binary_size?: number
        [key: string]: unknown
    }

    type AttributeGroup = {
        min_occurrence?: number
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttributeValueItem[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number
        }>(),
        {
            readOnly: false,
            edit: false,
            modify: false
        }
    )

    const { canModify, add, del } = useAttributes(props)

    const formatFileSize = (bytes: number | null | undefined): string => {
        if (!bytes) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + (sizes[i] ?? 'B')
    }

    const downloadAttachmentNow = (attrValue: AttributeValueItem): void => {
        if (!attrValue || !attrValue.id) return
        const fileName = attrValue.binary_description || 'attachment'
        const downloadLink = `/analyze/report-items/${props.reportItemId}/file-attributes/${attrValue.id}/file`
        downloadAttachment(downloadLink, fileName)
    }
</script>

<style scoped>
    .attachment-display {
        border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
        border-radius: 4px;
    }

    .value-holder {
        width: 100%;
        margin-bottom: 2px;
    }
</style>
