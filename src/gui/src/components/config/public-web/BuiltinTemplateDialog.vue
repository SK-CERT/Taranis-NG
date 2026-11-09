<template>
    <v-dialog
        v-model="open"
        max-width="1100"
        scrollable
    >
        <v-card v-if="template">
            <v-card-item>
                <v-card-title>
                    <code data-test="builtin-dialog-name">{{ template.name }}</code>
                </v-card-title>
                <v-card-subtitle
                    v-if="usedFor"
                    class="text-wrap"
                    >{{ usedFor }}</v-card-subtitle
                >
                <template #append>
                    <v-btn
                        variant="text"
                        size="small"
                        :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
                        data-test="builtin-dialog-copy"
                        @click="copy"
                    >
                        {{ copied ? t('public_web.templates.builtin_copied') : t('public_web.templates.builtin_copy') }}
                    </v-btn>
                    <v-btn
                        icon="mdi-close"
                        variant="text"
                        size="small"
                        :title="t('common.close')"
                        @click="open = false"
                    />
                </template>
            </v-card-item>
            <v-card-text>
                <v-alert
                    v-if="copyFailed"
                    type="error"
                    variant="tonal"
                    density="compact"
                    class="mb-2"
                >
                    {{ t('public_web.templates.builtin_copy_failed') }}
                </v-alert>
                <CodeEditor
                    :model-value="template.source"
                    readonly
                    :aria-label="template.name"
                    data-test="builtin-dialog-source"
                />
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import CodeEditor from '@/components/common/CodeEditor.vue'
    import type { PublicWebBuiltinTemplate } from '@/types/public-web-template'

    const props = withDefaults(
        defineProps<{
            template?: PublicWebBuiltinTemplate | null
            /** What the template is used for, as the list shows it. */
            usedFor?: string
        }>(),
        { template: null, usedFor: '' }
    )

    const open = defineModel<boolean>({ default: false })

    const { t } = useI18n()

    const copied = ref(false)
    const copyFailed = ref(false)

    watch([open, () => props.template], () => {
        copied.value = false
        copyFailed.value = false
    })

    async function copy(): Promise<void> {
        copyFailed.value = false
        try {
            await navigator.clipboard.writeText(props.template?.source ?? '')
            copied.value = true
        } catch {
            copied.value = false
            copyFailed.value = true
        }
    }
</script>
