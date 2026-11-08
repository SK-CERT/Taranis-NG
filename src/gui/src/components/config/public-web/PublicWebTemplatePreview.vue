<template>
    <div
        class="template-preview"
        data-test="template-preview"
    >
        <p class="text-body-medium text-medium-emphasis mb-3">{{ t('public_web.preview.intro') }}</p>

        <v-alert
            v-if="!hasTarget"
            type="info"
            variant="tonal"
            density="compact"
        >
            {{ t('public_web.preview.choose_target') }}
        </v-alert>

        <template v-else>
            <v-row density="compact">
                <v-col
                    cols="12"
                    md="4"
                >
                    <v-select
                        v-model="webId"
                        :items="webItems"
                        :label="t('public_web.preview.web')"
                        variant="outlined"
                        density="compact"
                        hide-details
                        data-test="preview-web"
                    />
                </v-col>
                <v-col
                    cols="6"
                    md="2"
                >
                    <v-select
                        v-model="language"
                        :items="languageItems"
                        :label="t('public_web.preview.language')"
                        variant="outlined"
                        density="compact"
                        hide-details
                        :disabled="languageItems.length < 2"
                        data-test="preview-language"
                    />
                </v-col>
                <v-col
                    cols="6"
                    md="6"
                >
                    <v-select
                        v-model="productId"
                        :items="productItems"
                        :label="t('public_web.preview.product')"
                        :no-data-text="t('public_web.preview.no_products')"
                        variant="outlined"
                        density="compact"
                        hide-details
                        data-test="preview-product"
                    />
                </v-col>
            </v-row>

            <div class="d-flex align-center flex-wrap ga-2 my-3">
                <v-btn-toggle
                    v-model="view"
                    mandatory
                    density="compact"
                    variant="outlined"
                    divided
                    data-test="preview-view"
                >
                    <v-btn value="detail">{{ t('public_web.preview.view_detail') }}</v-btn>
                    <v-btn value="summary">{{ t('public_web.preview.view_summary') }}</v-btn>
                    <v-btn value="rss">{{ t('public_web.preview.view_rss') }}</v-btn>
                </v-btn-toggle>
                <v-spacer />
                <v-progress-circular
                    v-if="loading"
                    indeterminate
                    size="20"
                    width="2"
                />
                <v-btn
                    variant="text"
                    size="small"
                    prepend-icon="mdi-open-in-new"
                    :disabled="!pageSrc"
                    data-test="preview-open"
                    @click="openPage"
                >
                    {{ t('public_web.preview.open_new_tab') }}
                </v-btn>
                <v-btn
                    variant="text"
                    size="small"
                    prepend-icon="mdi-refresh"
                    :disabled="loading"
                    data-test="preview-refresh"
                    @click="refresh"
                >
                    {{ t('public_web.preview.refresh') }}
                </v-btn>
            </div>

            <v-alert
                v-if="error"
                type="error"
                variant="tonal"
                density="compact"
                class="mb-3"
                data-test="preview-error"
            >
                {{ error }}
            </v-alert>

            <template v-if="result">
                <v-alert
                    v-if="result.errors.length"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                    data-test="preview-template-errors"
                >
                    <div class="mb-1">{{ t('public_web.preview.errors_title') }}</div>
                    <ul class="ps-4">
                        <li
                            v-for="(templateError, index) in result.errors"
                            :key="index"
                        >
                            <code>{{ templateError.template }}</code
                            ><span v-if="templateError.line">, {{ t('public_web.preview.line', { line: templateError.line }) }}</span
                            >: {{ templateError.message }}
                        </li>
                    </ul>
                </v-alert>
                <v-alert
                    v-for="(warning, index) in result.warnings"
                    :key="`warning-${index}`"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                    data-test="preview-warning"
                >
                    {{ warning }}
                </v-alert>

                <!-- Core serves the page with a policy of its own (the GUI's would block the web's
                     styles); sandboxed, without scripts or an origin, it cannot reach the GUI. -->
                <iframe
                    v-if="pageSrc"
                    class="template-preview__frame"
                    :src="pageSrc"
                    sandbox=""
                    :title="t('public_web.preview.title')"
                    data-test="preview-frame"
                />

                <v-card
                    v-else-if="result.rss"
                    variant="outlined"
                    data-test="preview-rss"
                >
                    <v-card-text>
                        <div class="text-title-medium mb-1">{{ result.rss.title }}</div>
                        <a
                            :href="result.rss.link"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-body-small"
                            >{{ result.rss.link }}</a
                        >
                        <div class="template-preview__description mt-3">{{ result.rss.description }}</div>
                        <div class="text-label-medium text-medium-emphasis mt-4 mb-1">{{ t('public_web.preview.xml') }}</div>
                        <pre class="template-preview__xml">{{ result.xml }}</pre>
                    </v-card-text>
                </v-card>
            </template>
        </template>
    </div>
</template>

<script setup lang="ts">
    /**
     * The preview of a report template being edited: a published product rendered with it by the
     * web's public-web node, as the web would show it - the report page, the homepage entry or
     * the whole RSS item. It follows the editor: a change is rendered a moment after typing stops.
     */
    import { computed, onBeforeUnmount, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { AxiosError } from 'axios'
    import { getPublicWebTemplatePreviewOptions, previewPublicWebTemplate } from '@/api/config'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import type { PreviewOptions, PreviewProduct, PreviewResult, PreviewView, PreviewWeb } from '@/types/public-web-template'

    const props = defineProps<{
        /** Whether the preview is shown: it asks the node only then. */
        active: boolean
        productPresetId: number | null
        reportItemTypeId: number | null
        source: string
        requireTlpClear: boolean
        publicWebIds: number[]
    }>()

    const { t } = useI18n()
    const { formatDate } = useLocaleFormatters()

    // How long after the last change to render it again.
    const DEBOUNCE_MS = 800

    const webs = ref<PreviewWeb[]>([])
    const products = ref<PreviewProduct[]>([])
    const webId = ref<number | null>(null)
    const language = ref<string | null>(null)
    const productId = ref<number | null>(null)
    const view = ref<PreviewView>('detail')
    const result = ref<PreviewResult | null>(null)
    const error = ref('')
    const loading = ref(false)
    let requestNumber = 0
    let timer: ReturnType<typeof setTimeout> | undefined

    const API_BASE = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || '/api/v1'

    const hasTarget = computed(() => props.productPresetId != null || props.reportItemTypeId != null)
    const currentWeb = computed(() => webs.value.find((web) => web.id === webId.value) ?? null)
    const pageSrc = computed(() => (result.value?.page_url ? `${API_BASE}${result.value.page_url}` : ''))

    const webItems = computed(() =>
        webs.value.map((web) => ({
            title: web.unavailable ? `${web.name} (${web.unavailable})` : web.name,
            value: web.id,
            props: { disabled: web.unavailable !== null }
        }))
    )
    const languageItems = computed(() => (currentWeb.value?.languages ?? []).map((code) => ({ title: code, value: code })))
    const productItems = computed(() =>
        products.value.map((product) => ({
            title: product.created ? `${product.title} (${formatDate(product.created)})` : product.title,
            value: product.id
        }))
    )

    const message = (reason: unknown): string => {
        const response = (reason as AxiosError<{ error?: string }>)?.response
        return response?.data?.error || t('public_web.preview.failed')
    }

    /** The webs and the products of the chosen one; the newest product and the web's language are picked. */
    async function loadOptions(chosenWebId: number | null = null): Promise<void> {
        if (!hasTarget.value) return
        try {
            const response = await getPublicWebTemplatePreviewOptions({
                product_preset_id: props.productPresetId,
                report_item_type_id: props.reportItemTypeId,
                web_id: chosenWebId,
                public_web_ids: props.publicWebIds
            })
            const options = (response as { data: PreviewOptions }).data
            webs.value = options.webs
            products.value = options.products
            webId.value = options.web_id
            if (!products.value.some((product) => product.id === productId.value)) {
                productId.value = products.value[0]?.id ?? null
            }
            const offered = currentWeb.value?.languages ?? []
            if (!language.value || !offered.includes(language.value)) {
                language.value = currentWeb.value?.default_language ?? offered[0] ?? null
            }
        } catch (reason) {
            error.value = message(reason)
        }
    }

    async function render(): Promise<void> {
        if (!props.active || !hasTarget.value) return
        if (webId.value == null || productId.value == null) {
            result.value = null
            error.value = currentWeb.value?.unavailable || (webs.value.length ? t('public_web.preview.no_products') : '')
            return
        }
        const number = ++requestNumber
        loading.value = true
        try {
            const response = await previewPublicWebTemplate({
                template: {
                    product_preset_id: props.productPresetId,
                    report_item_type_id: props.reportItemTypeId,
                    source: props.source,
                    require_tlp_clear: props.requireTlpClear,
                    public_web_ids: props.publicWebIds
                },
                web_id: webId.value,
                language: language.value,
                product_id: productId.value,
                view: view.value
            })
            if (number !== requestNumber) return
            result.value = (response as { data: PreviewResult }).data
            error.value = ''
        } catch (reason) {
            if (number !== requestNumber) return
            // The last good preview stays under the message: a typo shows what is wrong, not a blank.
            error.value = message(reason)
        } finally {
            if (number === requestNumber) loading.value = false
        }
    }

    function schedule(): void {
        clearTimeout(timer)
        timer = setTimeout(render, DEBOUNCE_MS)
    }

    /** The page in a browser tab of its own (a button, not a link: it looks like Refresh beside it). */
    function openPage(): void {
        if (pageSrc.value) window.open(pageSrc.value, '_blank', 'noopener,noreferrer')
    }

    async function refresh(): Promise<void> {
        clearTimeout(timer)
        await loadOptions(webId.value)
        await render()
    }

    // Opened, or a new target: what can be shown changes.
    watch(
        () => [props.active, props.productPresetId, props.reportItemTypeId] as const,
        async ([active]) => {
            if (!active) return
            result.value = null
            error.value = ''
            await loadOptions(webId.value)
            await render()
        },
        { immediate: true }
    )

    // Another web: its products and languages.
    watch(webId, async (next, previous) => {
        if (!props.active || previous === null || next === previous || next === null) return
        await loadOptions(next)
        schedule()
    })

    watch([language, productId, view], () => {
        if (props.active) schedule()
    })

    // The editor: render again a moment after typing stops.
    watch(
        () => [props.source, props.requireTlpClear] as const,
        () => {
            if (props.active) schedule()
        }
    )

    onBeforeUnmount(() => clearTimeout(timer))

    defineExpose({ refresh })
</script>

<style scoped>
    .template-preview__frame {
        width: 100%;
        height: max(32rem, calc(100vh - 26rem));
        border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
        border-radius: 4px;
        background: #fff;
    }

    .template-preview__description {
        white-space: pre-wrap;
    }

    .template-preview__xml {
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 0.8rem;
        padding: 0.75rem;
        border-radius: 4px;
        background: rgba(var(--v-theme-on-surface), 0.04);
    }
</style>
