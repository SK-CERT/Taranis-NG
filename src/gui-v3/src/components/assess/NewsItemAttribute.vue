<template>
    <v-container class="ma-0 pa-0">
        <v-row>
            <v-col>
                <span class="pe-6 font-weight-bold text-medium-emphasis">
                    <bdi dir="auto">{{ attribute.key }}</bdi>
                </span>
                <!-- add space to allow copy formatted -->
                <span>&nbsp;</span>
                <span v-if="attribute.binary_mime_type === ''">
                    <bdi dir="auto">{{ attribute.value }}</bdi>
                </span>
                <span
                    v-else
                    class="align-center"
                >
                    <v-icon class="pe-6">mdi-file-document</v-icon>
                    <bdi
                        class="pe-6"
                        dir="auto"
                        >{{ attribute.value }}</bdi
                    >
                    <v-btn
                        prepend-icon="mdi-cloud-download"
                        variant="outlined"
                        size="large"
                        @click="downloadFile"
                    >
                        {{ t('assess.download') }}
                    </v-btn>
                </span>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuthStore } from '@/stores/auth'
    import { downloadAttachment } from '@/api/analyze'

    type NewsAttribute = {
        id: number | string
        key?: string
        value?: string
        binary_mime_type?: string
        [key: string]: unknown
    }

    type NewsItemData = {
        id?: number | string
        [key: string]: unknown
    }

    const { t } = useI18n()
    const authStore = useAuthStore()

    const props = withDefaults(
        defineProps<{
            attribute: NewsAttribute
            newsItemData?: NewsItemData
        }>(),
        {
            newsItemData: () => ({})
        }
    )

    async function downloadFile() {
        const apiBase = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || ''
        downloadAttachment(`${apiBase}/assess/news-item-data/${props.newsItemData.id}/attributes/${props.attribute.id}/file`, undefined)
    }
</script>
