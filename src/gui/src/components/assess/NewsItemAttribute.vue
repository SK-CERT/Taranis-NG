<template>
    <v-container class="ma-0">
        <v-row>
            <v-col>
                <span style="margin-right: 20px; font-size: 12px">{{ attribute.key }}</span>
                <br />
                <span
                    v-if="attribute.binary_mime_type === ''"
                    style="font-size: 16px"
                >
                    {{ attribute.value }}
                </span>
                <v-row
                    v-if="attribute.binary_mime_type !== ''"
                    class="align-center"
                >
                    <v-col class="flex-grow-0">
                        <v-icon>mdi-file-document</v-icon>
                    </v-col>
                    <v-col>
                        <div>{{ attribute.value }}</div>
                    </v-col>
                    <v-col>
                        <v-btn
                            prepend-icon="mdi-cloud-download"
                            variant="outlined"
                            size="large"
                            @click="downloadFile"
                        >
                            {{ t('assess.download') }}
                        </v-btn>
                    </v-col>
                </v-row>
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
