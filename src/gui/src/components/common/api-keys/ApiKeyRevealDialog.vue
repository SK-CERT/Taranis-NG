<template>
    <v-dialog
        v-model="open"
        max-width="720"
        persistent
    >
        <v-card data-test="api-key-reveal">
            <v-toolbar
                color="primary"
                density="compact"
            >
                <v-toolbar-title>
                    <v-icon
                        class="me-2"
                        size="small"
                        >mdi-key-chain-variant</v-icon
                    >
                    {{ t('api_keys.reveal_title') }}
                </v-toolbar-title>
            </v-toolbar>

            <v-card-text>
                <p
                    v-if="name"
                    class="text-subtitle-1 mb-3"
                >
                    <bdi dir="auto">{{ name }}</bdi>
                </p>

                <v-alert
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mb-4"
                >
                    {{ t('api_keys.reveal_warning') }}
                </v-alert>

                <v-text-field
                    :model-value="apiKey"
                    readonly
                    dir="ltr"
                    variant="outlined"
                    density="comfortable"
                    hide-details
                    class="api-key-reveal__key"
                    data-test="api-key-plaintext"
                    @focus="selectAll"
                >
                    <template #append-inner>
                        <v-btn
                            :icon="copied ? 'mdi-check' : 'mdi-content-copy'"
                            :color="copied ? 'success' : undefined"
                            :title="t('api_keys.copy')"
                            :aria-label="t('api_keys.copy')"
                            variant="text"
                            size="small"
                            data-test="api-key-copy"
                            @click="copy"
                        />
                    </template>
                </v-text-field>
                <div
                    class="text-caption mt-1"
                    :class="copyFailed ? 'text-error' : 'text-success'"
                    role="status"
                    aria-live="polite"
                >
                    {{ copyFailed ? t('api_keys.copy_failed') : copied ? t('api_keys.copied') : '' }}
                </div>

                <p class="text-body-2 mt-3 mb-1">{{ t('api_keys.reveal_usage') }}</p>
                <pre
                    class="api-key-reveal__example"
                    dir="ltr"
                    data-test="api-key-example"
                    >{{ example }}</pre>
            </v-card-text>

            <v-card-actions>
                <v-spacer />
                <v-btn
                    color="primary"
                    variant="flat"
                    prepend-icon="mdi-check"
                    data-test="api-key-reveal-done"
                    @click="open = false"
                >
                    {{ t('api_keys.reveal_done') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import axios from 'axios'
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'

    const props = defineProps<{
        modelValue: boolean
        /** The new key's plaintext: shown here once and never again. */
        apiKey: string
        name?: string
    }>()

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
    }>()

    const { t } = useI18n()
    const copied = ref(false)
    const copyFailed = ref(false)

    const open = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })

    // The API base the GUI itself talks to, so the example works as pasted.
    const apiBase = computed(() => {
        try {
            return new URL(String(axios.defaults.baseURL || '/api/v1'), window.location.origin).href.replace(/\/$/u, '')
        } catch {
            return `${window.location.origin}/api/v1`
        }
    })
    const example = computed(() => `curl -H "Authorization: ApiKey ${props.apiKey}" \\\n    ${apiBase.value}/assess/osint-source-groups`)

    watch(
        () => props.modelValue,
        () => {
            copied.value = false
            copyFailed.value = false
        }
    )

    const selectAll = (event: FocusEvent): void => {
        ;(event.target as { select?: () => void } | null)?.select?.()
    }

    const copy = async (): Promise<void> => {
        copyFailed.value = false
        try {
            await navigator.clipboard.writeText(props.apiKey)
            copied.value = true
        } catch {
            copied.value = false
            copyFailed.value = true
        }
    }
</script>

<style scoped>
    .api-key-reveal__key :deep(input) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.9rem;
    }

    .api-key-reveal__example {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.8rem;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        padding: 0.75rem;
        border-radius: 4px;
        background: rgba(var(--v-theme-on-surface), 0.06);
        margin: 0;
    }
</style>
