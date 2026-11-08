<template>
    <v-dialog
        v-model="open"
        :max-width="sideBySide ? 1800 : 1100"
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
                <!-- The source and the preview side by side when the dialog is wide enough, on two tabs otherwise. -->
                <v-tabs
                    v-if="!sideBySide"
                    v-model="activeTab"
                    color="primary"
                    density="comfortable"
                    class="mb-3"
                >
                    <v-tab
                        value="template"
                        prepend-icon="mdi-code-braces"
                        data-test="builtin-tab-source"
                        >{{ t('public_web.templates.tab_template') }}</v-tab
                    >
                    <v-tab
                        value="preview"
                        prepend-icon="mdi-eye-outline"
                        data-test="builtin-tab-preview"
                        >{{ t('public_web.preview.title') }}</v-tab
                    >
                </v-tabs>

                <v-alert
                    v-if="copyFailed"
                    type="error"
                    variant="tonal"
                    density="compact"
                    class="mb-2"
                >
                    {{ t('public_web.templates.builtin_copy_failed') }}
                </v-alert>

                <div
                    class="builtin-panes"
                    :class="{ 'builtin-panes--split': sideBySide }"
                >
                    <div v-show="showSource">
                        <div
                            v-if="sideBySide"
                            class="builtin-panes__heading"
                        >
                            <span class="text-title-small">{{ t('public_web.templates.source') }}</span>
                        </div>
                        <CodeEditor
                            :model-value="template.source"
                            readonly
                            :aria-label="template.name"
                            :max-height="sideBySide ? SPLIT_EDITOR_HEIGHT : 'none'"
                            data-test="builtin-dialog-source"
                        />
                    </div>
                    <div v-show="showPreview">
                        <div
                            v-if="sideBySide"
                            class="builtin-panes__heading"
                        >
                            <span class="text-title-small">{{ t('public_web.preview.title') }}</span>
                        </div>
                        <!-- Rendered with the built-ins alone, on a published product this one shows in. -->
                        <PublicWebTemplatePreview
                            :active="open && showPreview"
                            :builtin="template.name"
                        />
                    </div>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useDisplay } from 'vuetify'
    import CodeEditor from '@/components/common/CodeEditor.vue'
    import PublicWebTemplatePreview from './PublicWebTemplatePreview.vue'
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

    // As the template dialog: side by side from this window width (the dialog then up to
    // 1800 px), on two tabs below it, the preview rendering only on its own tab.
    const SIDE_BY_SIDE_MIN_WIDTH = 1400
    const SPLIT_EDITOR_HEIGHT = 'max(32rem, calc(100vh - 18rem))'
    const { width: windowWidth } = useDisplay()
    const sideBySide = computed(() => windowWidth.value >= SIDE_BY_SIDE_MIN_WIDTH)
    const activeTab = ref<'template' | 'preview'>('template')
    const showSource = computed(() => sideBySide.value || activeTab.value === 'template')
    const showPreview = computed(() => sideBySide.value || activeTab.value === 'preview')

    const copied = ref(false)
    const copyFailed = ref(false)

    watch([open, () => props.template], () => {
        copied.value = false
        copyFailed.value = false
    })

    // Another built-in opens on its source.
    watch(
        () => props.template,
        () => {
            activeTab.value = 'template'
        }
    )

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

<style scoped>
    .builtin-panes--split {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 1.5rem;
        align-items: start;
    }

    /* The same height on both sides, so the source and the preview start level. */
    .builtin-panes__heading {
        display: flex;
        align-items: center;
        min-height: 2.25rem;
        margin-bottom: 0.25rem;
    }
</style>
