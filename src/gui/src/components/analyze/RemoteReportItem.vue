<template>
    <v-dialog
        v-model="visible"
        fullscreen
        persistent
        @keydown.esc="handleClose"
    >
        <v-card>
            <v-toolbar
                color="primary"
                dark
            >
                <v-btn
                    icon
                    @click="handleClose"
                >
                    <v-icon>mdi-close-circle</v-icon>
                </v-btn>
                <v-toolbar-title>{{ reportItem.title }}</v-toolbar-title>
                <v-spacer />
            </v-toolbar>

            <v-card-text class="pa-6">
                <div>
                    <strong>{{ t('report_item.id') }}:</strong>
                    <span>{{ reportItem.uuid }}</span>
                </div>

                <v-divider class="my-4" />

                <h3 class="text-h6 mb-4">
                    {{ t('report_item.attributes') }}
                </h3>
                <v-container v-if="reportItem.attributes && reportItem.attributes.length > 0">
                    <RemoteAttributeContainer
                        v-for="attribute in reportItem.attributes"
                        :key="attribute.id"
                        :attribute-group="attribute"
                        :report-item-id="Number(reportItem.id || 0)"
                    />
                </v-container>
                <v-alert
                    v-else
                    type="info"
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

    type RemoteAttributeGroup = {
        id: number | string
        attribute?: {
            attribute_type?: string
            [key: string]: unknown
        }
        [key: string]: unknown
    }

    type RemoteReportItemModel = {
        id: number | string | null
        title: string
        uuid: string
        attributes: RemoteAttributeGroup[]
        [key: string]: unknown
    }

    type ApiResponse<T> = {
        data?: T
    }

    const visible = ref<boolean>(false)
    const reportItem = ref<RemoteReportItemModel>({
        id: null,
        title: '',
        uuid: '',
        attributes: []
    })

    const normalizeReportItem = (payload: unknown, fallback: RemoteReportItemModel): RemoteReportItemModel => {
        if (payload && typeof payload === 'object') {
            const candidate = payload as Partial<RemoteReportItemModel>
            if (candidate.id !== undefined && candidate.title !== undefined && candidate.uuid !== undefined) {
                return {
                    id: candidate.id ?? fallback.id,
                    title: typeof candidate.title === 'string' ? candidate.title : fallback.title,
                    uuid: typeof candidate.uuid === 'string' ? candidate.uuid : fallback.uuid,
                    attributes: Array.isArray(candidate.attributes) ? candidate.attributes : fallback.attributes
                }
            }
        }
        return fallback
    }

    const showDetail = async (item: RemoteReportItemModel): Promise<void> => {
        try {
            if (item.id == null) {
                reportItem.value = item
                visible.value = true
                return
            }

            const response = (await getReportItem(item.id)) as ApiResponse<unknown> | unknown
            const responseData =
                response && typeof response === 'object' && 'data' in response ? (response as ApiResponse<unknown>).data : response

            reportItem.value = normalizeReportItem(responseData, item)
            visible.value = true
        } catch {
            // Fallback to passed item data
            reportItem.value = item
            visible.value = true
        }
    }

    const handleClose = (): void => {
        visible.value = false
    }

    defineExpose({
        showDetail
    })
</script>
