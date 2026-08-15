<template>
    <v-dialog
        v-model="visible"
        fullscreen
        persistent
        @keydown.esc="handleClose"
    >
        <v-card class="remote-report">
            <v-toolbar color="primary">
                <v-btn
                    icon
                    :title="t('notification.close')"
                    @click="handleClose"
                >
                    <v-icon>mdi-close-circle</v-icon>
                </v-btn>
                <v-toolbar-title
                    ><bdi dir="auto">{{ reportItem.title }}</bdi></v-toolbar-title
                >
            </v-toolbar>

            <v-card-text class="remote-report__body">
                <v-alert
                    type="info"
                    variant="tonal"
                    class="mb-4"
                >
                    <div class="remote-report__identity">
                        <i18n-t
                            scope="global"
                            keypath="report_item.id_with_value"
                        >
                            <template #id>
                                <bdi dir="ltr">{{ reportItem.uuid }}</bdi>
                            </template>
                        </i18n-t>
                        <i18n-t
                            v-if="reportItem.remote_user"
                            scope="global"
                            keypath="card_item.source_with_value"
                        >
                            <template #source>
                                <bdi dir="auto">{{ reportItem.remote_user }}</bdi>
                            </template>
                        </i18n-t>
                    </div>
                </v-alert>

                <h2 class="text-h6 mb-3">
                    {{ t('report_item.attributes') }}
                </h2>
                <div
                    v-if="reportItem.attributes.length > 0"
                    class="remote-report__attributes"
                >
                    <RemoteAttributeContainer
                        v-for="attribute in reportItem.attributes"
                        :key="attribute.id"
                        :attribute-group="attribute"
                        :report-item-id="Number(reportItem.id)"
                    />
                </div>
                <v-alert
                    v-else
                    type="info"
                    variant="tonal"
                >
                    {{ t('report_item.no_attributes') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import RemoteAttributeContainer from '@/components/common/attribute/RemoteAttributeContainer.vue'
    import { getReportItem } from '@/api/analyze'

    const { t } = useI18n()

    type RemoteAttributeValue = {
        id: number | string
        value?: string
        binary_mime_type?: string | null
        binary_size?: number | null
        binary_description?: string | null
        attribute_group_item_title?: string | null
        [key: string]: unknown
    }

    type RemoteAttributeGroup = {
        id: string
        title: string
        attributeType: string
        attributes: RemoteAttributeValue[]
    }

    type RemoteReportItemSummary = {
        id: number | string
        title?: string
        uuid?: string
        remote_user?: string | null
        [key: string]: unknown
    }

    type RemoteReportItemModel = {
        id: number | string
        title: string
        uuid: string
        remote_user: string
        attributes: RemoteAttributeGroup[]
    }

    const emptyReportItem = (): RemoteReportItemModel => ({
        id: 0,
        title: '',
        uuid: '',
        remote_user: '',
        attributes: []
    })

    const visible = ref(false)
    const reportItem = ref<RemoteReportItemModel>(emptyReportItem())

    const groupAttributes = (attributes: unknown): RemoteAttributeGroup[] => {
        if (!Array.isArray(attributes)) return []

        const groups = new Map<string, RemoteAttributeGroup>()
        for (const candidate of attributes) {
            if (!candidate || typeof candidate !== 'object') continue
            const value = candidate as RemoteAttributeValue
            const title = value.attribute_group_item_title?.trim() || t('attribute.unknown_type')
            const attributeType = value.binary_mime_type ? 'ATTACHMENT' : 'TEXT'
            const key = `${title}\u0000${attributeType}`
            let group = groups.get(key)
            if (!group) {
                group = { id: key, title, attributeType, attributes: [] }
                groups.set(key, group)
            }
            group.attributes.push(value)
        }
        return Array.from(groups.values())
    }

    const showDetail = async (item: RemoteReportItemSummary): Promise<void> => {
        if (item.id === null || item.id === undefined || item.remote_user === null || item.remote_user === undefined) return

        try {
            const response = await getReportItem(item.id)
            const data = response?.data
            if (!data || data.remote_user === null || data.remote_user === undefined) return

            reportItem.value = {
                id: data.id,
                title: typeof data.title === 'string' ? data.title : item.title || '',
                uuid: typeof data.uuid === 'string' ? data.uuid : item.uuid || '',
                remote_user: String(data.remote_user),
                attributes: groupAttributes(data.attributes)
            }
            visible.value = true
        } catch {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', message: t('error.server_error') }
                })
            )
        }
    }

    const handleClose = (): void => {
        visible.value = false
        reportItem.value = emptyReportItem()
    }

    defineExpose({ showDetail })
</script>

<style scoped>
    .remote-report__body {
        width: min(100%, 1080px);
        margin-inline: auto;
        padding: 1.5rem;
    }

    .remote-report__identity {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem 1.5rem;
    }

    .remote-report__attributes {
        display: grid;
        gap: 0.75rem;
    }
</style>
