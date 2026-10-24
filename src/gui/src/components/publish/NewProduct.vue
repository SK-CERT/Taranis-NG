<template>
    <v-dialog
        v-model="visible"
        fullscreen
        persistent
        @keydown.esc.stop="handleCancel"
        @after-leave="resetForm"
    >
        <!-- Confirmation dialogs -->
        <v-dialog
            v-model="showCloseConfirmation"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ $t('confirm_close.title') }}
                </v-card-title>
                <v-card-text>{{ $t('product.confirm_close.message') }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        color="primary"
                        variant="elevated"
                        class="confirm-btn"
                        @click="showCloseConfirmation = false"
                    >
                        {{ $t('confirm_close.continue') }}
                    </v-btn>
                    <v-btn
                        color="success"
                        variant="elevated"
                        class="confirm-btn"
                        @click="saveAndClose"
                    >
                        {{ $t('confirm_close.save_and_close') }}
                    </v-btn>
                    <v-btn
                        color="error"
                        variant="elevated"
                        class="confirm-btn"
                        @click="confirmClose"
                    >
                        {{ $t('confirm_close.close') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <ConfirmationDialog
            v-model="showPublishConfirmation"
            title-key="product.publish_confirmation"
            confirm-label-key="common.yes"
            max-width="500px"
            @confirm="handlePublish"
        >
            <div class="text-body-1 font-weight-bold mb-2">
                <bdi dir="auto">{{ product.title }}</bdi>
            </div>
            <div class="mb-1">
                <i18n-t
                    scope="global"
                    keypath="product.publish_confirmation_type"
                >
                    <template #type>
                        <bdi dir="auto">{{ selectedType?.title || $t('product.no_type') }}</bdi>
                    </template>
                </i18n-t>
            </div>
            <div class="mb-1">
                <i18n-t
                    scope="global"
                    keypath="product.publish_confirmation_publishers"
                >
                    <template #publishers>
                        <bdi
                            v-if="selectedPublisherPresetNames.length > 0"
                            dir="auto"
                            >{{ selectedPublisherPresetList }}</bdi
                        >
                        <span
                            v-else
                            class="text-grey"
                        >
                            {{ $t('product.no_publisher_in_dialog') }}
                        </span>
                    </template>
                </i18n-t>
            </div>
            <v-select
                v-if="renderLanguages.length > 1"
                v-model="publishLanguage"
                :items="renderLanguages.map((code) => ({ title: languageName(code), value: code }))"
                :label="$t('product.publish_in')"
                density="compact"
                variant="outlined"
                class="mt-3"
                data-test="publish-language"
            />
            <div
                v-else-if="publishLanguage"
                class="mb-1"
            >
                {{ $t('product.publish_in_language', { language: languageName(publishLanguage) }) }}
            </div>
            <ProductLanguageNotices
                :check="publishCheck"
                :language="publishLanguage"
            />
            <div class="text-body-2 text-grey mt-3">
                {{ $t('product.publish_confirmation_message') }}
            </div>
        </ConfirmationDialog>

        <ConfirmationDialog
            v-model="showOutdatedConfirmation"
            title-key="product.outdated_confirmation"
            confirm-label-key="product.outdated_continue"
            max-width="500px"
            @confirm="continueWithOutdated"
        >
            <ProductLanguageNotices
                :check="outdatedCheck ? { ...outdatedCheck, missing: [], template_language: renderLanguage } : null"
                :language="renderLanguage"
            />
        </ConfirmationDialog>

        <v-dialog
            v-model="showPublishUnsavedConfirmation"
            max-width="500px"
            persistent
        >
            <v-card>
                <v-card-title class="text-h5">
                    {{ $t('product.publish_unsaved.title') }}
                </v-card-title>
                <v-card-text>{{ $t('product.publish_unsaved.message') }}</v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn @click="showPublishUnsavedConfirmation = false">
                        {{ $t('product.publish_unsaved.close') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        @click="saveAndPublish"
                    >
                        {{ $t('product.publish_unsaved.save_and_publish') }}
                    </v-btn>
                    <v-btn
                        color="error"
                        @click="publishOnly"
                    >
                        {{ $t('product.publish_unsaved.publish_only') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Main dialog -->
        <v-card class="d-flex flex-column h-100">
            <v-toolbar
                color="primary"
                dark
            >
                <v-btn
                    icon
                    @click="handleCancel"
                >
                    <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
                </v-btn>
                <v-toolbar-title>
                    {{ isEditMode ? $t('product.edit') : $t('product.add_new') }}
                </v-toolbar-title>
                <v-spacer />
                <ContentLanguageSelect
                    :model-value="product.language"
                    :label="$t('product.language')"
                    :disabled="!canModify"
                    class="me-4"
                    data-test="product-source-language"
                    @update:model-value="changeLanguage"
                />
                <StateSelector
                    v-if="availableStates.length > 0"
                    :model-value="product.state_id ?? ''"
                    :available-states="availableStates"
                    :label="$t('product.state')"
                    :disabled="!canModify"
                    class="me-4"
                    @update:model-value="handleStateChange"
                />
                <v-btn
                    v-if="!isEditMode && canModify && product.id === -1"
                    text
                    @click="handleSave"
                >
                    <v-icon start>
                        {{ ICONS.CONTENT_SAVE }}
                    </v-icon>
                    {{ $t('common.save') }}
                </v-btn>
            </v-toolbar>

            <v-card-text class="pa-4 overflow-y-auto bg-background">
                <ProductLanguageBar
                    v-model="activeLanguage"
                    :language="product.language"
                    :languages="productLanguages"
                    :statuses="tabStatuses"
                    :can-modify="canModify"
                    :translating="translatingTitle"
                    @translate-all="translateTitles(productLanguages)"
                />
                <ProductLanguageNotices
                    :check="currentCheck"
                    :language="renderLanguage"
                />
                <v-form
                    ref="formRef"
                    validate-on="submit"
                    @submit.prevent="handleSave"
                >
                    <v-row>
                        <v-col
                            v-if="tagsStore.adminTags('product').length > 0"
                            cols="12"
                        >
                            <TagPicker
                                entity-type="product"
                                :model-value="product.tag_ids"
                                :disabled="!canModify"
                                @update:model-value="changeTags"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-combobox
                                v-model="selectedType"
                                dir="auto"
                                :items="productTypes"
                                :item-title="(item) => item?.title || ''"
                                :label="$t('product.report_type')"
                                :rules="[requiredRule]"
                                :disabled="!canModify"
                                return-object
                                @update:model-value="handleProductTypeChange"
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-text-field
                                v-model="titleModel"
                                dir="auto"
                                :spellcheck="spellcheck"
                                :label="$t('product.title')"
                                :hint="activeLanguage === 'source' ? '' : product.title"
                                :persistent-hint="activeLanguage !== 'source'"
                                :rules="activeLanguage === 'source' ? [requiredRule] : []"
                                :disabled="!canModify"
                                data-test="product-title"
                                @blur="handleUpdateRecord"
                            >
                                <template
                                    v-if="activeLanguage !== 'source'"
                                    #append-inner
                                >
                                    <TranslationState
                                        :state="titleState"
                                        :reviewable="canModify"
                                        @review="reviewTitle"
                                    />
                                    <v-btn
                                        v-if="canModify && product.title"
                                        icon="mdi-translate"
                                        variant="text"
                                        density="compact"
                                        size="small"
                                        tabindex="-1"
                                        :loading="translatingTitle"
                                        :title="$t('report_item.translation.translate_field')"
                                        data-test="translate-product-title"
                                        @mousedown.stop
                                        @click.stop="translateTitles([activeLanguage])"
                                    />
                                </template>
                            </v-text-field>
                        </v-col>
                        <v-col cols="12">
                            <v-textarea
                                :ref="(field) => setDescriptionField(0, field)"
                                v-model="product.description"
                                dir="auto"
                                :spellcheck="spellcheck"
                                :label="$t('product.description')"
                                :disabled="!canModify"
                                rows="3"
                                @blur="onDescriptionBlur"
                                @keyup="trackDescriptionSelection(0)"
                                @click="trackDescriptionSelection(0)"
                            >
                                <template #append-inner>
                                    <CiteMenu
                                        :links="productCitableLinks"
                                        :groups="reportLinkGroups"
                                        :disabled="!canModify"
                                        @pick="(link) => citeInDescription(0, link.key)"
                                        @pick-external="citeReportLink"
                                    />
                                </template>
                            </v-textarea>
                            <ReferencePreview
                                :text="product.description"
                                :resolve="resolveProductCitation"
                            />
                        </v-col>
                        <v-col cols="12">
                            <div class="text-title-medium">
                                {{ $t('links.product_title') }}
                            </div>
                            <div class="text-body-2 text-medium-emphasis mb-1">
                                {{ $t('links.product_hint') }}
                            </div>
                            <LinkListEditor
                                :values="productLinks"
                                :disabled="!canModify"
                                :citation-count="productCitationCount"
                                @insert="insertProductLink"
                                @remove="removeProductLink"
                                @move="moveProductLink"
                                @blur="handleUpdateRecord"
                            />
                        </v-col>
                    </v-row>

                    <!-- Report Items Section -->
                    <v-row>
                        <v-col cols="12">
                            <v-btn
                                v-if="canModify"
                                :prepend-icon="ICONS.PLUS"
                                color="primary"
                                variant="flat"
                                class="mb-3"
                                @click="openReportItemSelector"
                            >
                                {{ $t('report_item.select') }}
                            </v-btn>

                            <ReportItemSelector
                                ref="reportItemSelector"
                                :values="reportItems"
                                :modify="canModify"
                                :edit="isEditMode"
                                :product-state-is-final="productStateIsFinal"
                                @items-changed="handleReportItemsChanged"
                            />
                        </v-col>
                    </v-row>

                    <!-- Publisher Presets + Public Websites -->
                    <v-row>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <div class="text-title-medium mb-2">
                                {{ $t('product.publisher_presets') }}
                            </div>
                            <div v-if="publisherPresets.length > 0">
                                <v-checkbox
                                    v-for="preset in publisherPresets"
                                    :key="preset.id"
                                    v-model="preset.selected"
                                    :disabled="!canModify"
                                    hide-details
                                    density="compact"
                                >
                                    <template #label>
                                        <bdi dir="auto">{{ preset.name }}</bdi>
                                    </template>
                                </v-checkbox>
                            </div>
                            <div
                                v-else
                                class="text-center text-grey py-4"
                            >
                                {{ $t('common.no_data') }}
                            </div>
                        </v-col>

                        <v-col
                            v-if="showPublicWebSelection"
                            cols="12"
                            md="6"
                        >
                            <div class="text-title-medium mb-2">
                                {{ $t('product.public_web_targets') }}
                            </div>
                            <v-checkbox
                                v-for="web in publicWebOptions"
                                :key="web.id"
                                v-model="product.public_web_ids"
                                :label="web.name"
                                :value="web.id"
                                :disabled="!canModify"
                                hide-details
                                density="compact"
                                @update:model-value="handlePublicWebSelectionChange"
                            />
                        </v-col>
                    </v-row>

                    <!-- Action Buttons -->
                    <v-row class="mt-4">
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-btn
                                :prepend-icon="ICONS.READ_OUTLINE"
                                color="primary"
                                variant="flat"
                                @click="handlePreview"
                            >
                                {{ $t('product.preview') }}
                            </v-btn>
                            <v-btn
                                class="ms-2"
                                :prepend-icon="ICONS.DOWNLOAD"
                                color="primary"
                                variant="flat"
                                @click="handleDownload"
                            >
                                {{ $t('common.download') }}
                            </v-btn>
                        </v-col>
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <v-btn
                                v-if="canPublish"
                                :prepend-icon="ICONS.SEND_OUTLINE"
                                color="primary"
                                variant="flat"
                                @click="handlePublishConfirmation"
                            >
                                {{ $t('product.publish') }}
                            </v-btn>
                        </v-col>
                    </v-row>

                    <!-- Error Messages -->
                    <v-row v-if="showError">
                        <v-col cols="12">
                            <v-alert
                                type="error"
                                variant="tonal"
                            >
                                {{ $t('product.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
    import { storeToRefs } from 'pinia'
    import { useI18n } from 'vue-i18n'
    import { useAuthStore } from '@/stores/auth'
    import { usePublishStore } from '@/stores/publish'
    import ApiService from '@/services/api_service'
    import { ICONS } from '@/config/ui-constants'
    import {
        createProduct,
        updateProduct,
        publishProduct,
        previewProduct,
        getProductById,
        translateProductTitle,
        checkProductLanguage
    } from '@/api/publish'
    import { getAllUserProductTypes, getAllUserPublishersPresets } from '@/api/user'
    import { getEntityTypeStates } from '@/api/state'
    import { useAuth } from '@/composables/useAuth'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { navigateReservedTabOrCurrentWindow, openBlankTabWithoutOpener } from '@/utils/window'
    import StateSelector from '@/components/common/StateSelector.vue'
    import ContentLanguageSelect from '@/components/common/ContentLanguageSelect.vue'
    import TagPicker from '@/components/common/tags/TagPicker.vue'
    import { useTagsStore } from '@/stores/tags'
    import { translationStatus } from '@/utils/translationStatus'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import ReportItemSelector from '@/components/publish/ReportItemSelector.vue'
    import ProductLanguageBar from '@/components/publish/ProductLanguageBar.vue'
    import ProductLanguageNotices, { type LanguageCheck } from '@/components/publish/ProductLanguageNotices.vue'
    import TranslationState, { type TranslationStateValue } from '@/components/analyze/TranslationState.vue'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import CiteMenu from '@/components/common/links/CiteMenu.vue'
    import LinkListEditor from '@/components/common/links/LinkListEditor.vue'
    import ReferencePreview from '@/components/common/links/ReferencePreview.vue'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    import { useCitingField } from '@/composables/useCitingField'
    import { citedKeys, generateLinkKey, numberLinks, type ExternalLink, type LinkValue } from '@/utils/linkReferences'

    type ProductModel = {
        id: number
        title: string
        description: string
        product_type_id: number | string | undefined
        state_id: number | string | undefined
        report_items: Array<{ id: number | string }>
        public_web_ids: Array<number | string>
        links: ProductLink[]
        // The language the product is written in; null while not set.
        language: string | null
        // Its title in other languages, saved with the product.
        translations: Record<string, { title: string; origin: 'ai' | 'manual' }>
        // The tags people put on it, saved with the product.
        tag_ids: number[]
    }

    /** A source of the product, cited from its description by key. */
    type ProductLink = {
        key: string
        url: string
    }

    type FormRef = {
        reset?: () => void
        validate?: () => Promise<{ valid: boolean }>
    }

    type ReportItem = {
        id: number | string
        title?: string
        links?: Array<{ key: string | null; url: string }>
        // The languages of its report type.
        type_languages?: string[]
        [key: string]: unknown
    }

    type PublisherPreset = {
        id: number | string
        name: string
        selected: boolean
        [key: string]: unknown
    }

    type AvailableState = {
        id: number | string
        title?: string
        is_default?: boolean
        state_type?: string
        [key: string]: unknown
    }

    type ProductType = {
        id: number | string
        title?: string
        [key: string]: unknown
    }

    type ProductEditPayload = {
        id: number
        title: string
        description: string
        product_type_id: number | string | undefined
        state_id: number | string | undefined
        report_items?: ReportItem[]
        public_web_ids?: Array<number | string>
        links?: ProductLink[]
        modify: boolean
        access: boolean
    }

    type ProductDetailPayload = {
        id: number
        title: string
        description?: string
        product_type_id: number | string | undefined
        state_id: number | string | undefined
        report_items?: ReportItem[]
        public_web_ids?: Array<number | string>
        links?: ProductLink[]
        language?: string | null
        translations?: Record<string, { title?: TranslationStateValue }>
        tags?: number[]
    }

    const { t } = useI18n()
    const { formatList } = useLocaleFormatters()
    const tagsStore = useTagsStore()
    const spellcheck = useSpellcheck()
    const { checkPermission } = useAuth()
    const authStore = useAuthStore()
    const publishStore = usePublishStore()
    const { publicWebOptions } = storeToRefs(publishStore)

    // Component state
    const visible = ref<boolean>(false)
    const isEditMode = ref<boolean>(false)
    const showError = ref<boolean>(false)
    const showCloseConfirmation = ref<boolean>(false)
    const showPublishConfirmation = ref<boolean>(false)
    const showPublishUnsavedConfirmation = ref<boolean>(false)
    const initialFormState = ref<string | null>(null)
    const formRef = ref<FormRef | null>(null)
    const canModifyFlag = ref<boolean>(false)
    const canAccessFlag = ref<boolean>(false)

    // Form data
    const product = ref<ProductModel>({
        id: -1,
        title: '',
        description: '',
        product_type_id: undefined,
        state_id: undefined,
        report_items: [],
        public_web_ids: [],
        links: [],
        language: null,
        translations: {},
        tag_ids: []
    })

    const selectedType = ref<ProductType | null>(null)
    const reportItems = ref<ReportItem[]>([])
    const productTypes = ref<ProductType[]>([])
    const publisherPresets = ref<PublisherPreset[]>([])
    const availableStates = ref<AvailableState[]>([])
    const reportItemSelector = ref<{ openSelector?: () => void } | null>(null)

    // ---- Links ----
    // Edited in the shape of report attribute values (URL in value, key in value_description),
    // which is what the link list editor works on; prepareProduct turns them into product links.
    const productLinks = ref<LinkValue[]>([])

    const toLinkValues = (links: ProductLink[] | undefined): LinkValue[] =>
        (links || []).map((link) => ({ value: link.url, value_description: link.key }))

    const takenLinkKeys = (): string[] => productLinks.value.map((link) => String(link.value_description ?? ''))

    // The product's own links are numbered first; the links of its reports follow (as core does).
    const productCitableLinks = computed(() => numberLinks(productLinks.value))
    const allCitableLinks = computed(() =>
        numberLinks([
            ...productLinks.value,
            ...reportItems.value.flatMap((item) => (item.links || []).map((link) => ({ value: link.url, value_description: link.key })))
        ])
    )
    const citableByKey = computed(() => new Map(allCitableLinks.value.map((link) => [link.key, link])))
    const resolveProductCitation = (key: string) => citableByKey.value.get(key)

    const productCitationCount = (key: string): number => citedKeys(product.value.description).filter((cited) => cited === key).length

    const reportLinkGroups = computed(() =>
        reportItems.value
            .filter((item) => (item.links || []).length > 0)
            .map((item) => ({ title: String(item.title || item.id), links: (item.links || []) as ExternalLink[] }))
    )

    // ---- Languages ----
    // The open tab is the language the product is previewed, downloaded and published in.
    const { languageName, defaultContentLanguage } = useContentLanguages()
    const activeLanguage = ref<string>('source')
    const titleStates = ref<Record<string, { title?: TranslationStateValue }>>({})
    const translatingTitle = ref<boolean>(false)
    // The last language check, with what it was made for (see checkKey).
    const languageCheck = ref<{ key: string; check: LanguageCheck | null } | null>(null)
    const publishLanguage = ref<string | null>(null)
    const publishCheck = ref<LanguageCheck | null>(null)
    const showOutdatedConfirmation = ref<boolean>(false)
    const pendingOutdatedAction = ref<(() => void) | null>(null)
    // The check whose outdated translations the confirmation lists.
    const outdatedCheck = ref<LanguageCheck | null>(null)
    // Outdated translations were confirmed for these languages since the dialog opened.
    const outdatedConfirmed = ref<Set<string>>(new Set())

    /** The product's languages besides its own: those of its reports' types. */
    const productLanguages = computed<string[]>(() => {
        const languages: string[] = []
        for (const item of reportItems.value) {
            for (const language of item.type_languages ?? []) {
                if (language !== product.value.language && !languages.includes(language)) languages.push(language)
            }
        }
        return languages
    })
    // The title's translation status per tab: a stored outdated title stays outdated until edited.
    const tabStatuses = computed<Record<string, string>>(() =>
        Object.fromEntries(
            productLanguages.value.map((language) => {
                const local = product.value.translations[language]
                const stored = titleStates.value[language]?.title
                const row = local?.title
                    ? { value: local.title, origin: local.origin, outdated: Boolean(stored?.outdated) && local.title === stored?.value }
                    : null
                return [language, translationStatus(product.value.title ? [{ original: product.value.title, row }] : [])]
            })
        )
    )
    // The open tab's title as the form has it: typed by a person, it is no longer the AI's, nor outdated.
    const titleState = computed<TranslationStateValue | null>(() => {
        const stored = titleStates.value[activeLanguage.value]?.title
        const local = product.value.translations[activeLanguage.value]
        if (!stored || !local?.title) return stored ?? null
        return { ...stored, origin: local.origin, outdated: stored.outdated && local.title === stored.value }
    })
    const renderLanguage = computed<string | null>(() => (activeLanguage.value === 'source' ? product.value.language : activeLanguage.value))
    const renderLanguages = computed<string[]>(() => [...(product.value.language ? [product.value.language] : []), ...productLanguages.value])

    const titleModel = computed<string>({
        get: () =>
            activeLanguage.value === 'source' ? product.value.title : (product.value.translations[activeLanguage.value]?.title ?? ''),
        set: (value: string) => {
            if (activeLanguage.value === 'source') {
                product.value.title = value
                return
            }
            // Typed by a person: no longer the AI's.
            product.value.translations = { ...product.value.translations, [activeLanguage.value]: { title: value, origin: 'manual' } }
        }
    })

    function resetLanguages(): void {
        activeLanguage.value = 'source'
        titleStates.value = {}
        languageCheck.value = null
        outdatedConfirmed.value = new Set()
    }

    const notifyServerError = (error: unknown, fallback: string): void => {
        const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error
        window.dispatchEvent(
            new CustomEvent('notification', { detail: message ? { type: 'error', message } : { type: 'error', loc: fallback } })
        )
    }

    async function changeLanguage(language: string): Promise<void> {
        if (language === product.value.language) return
        if (product.value.translations[language]?.title) {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'product.language_in_use' } }))
            return
        }
        product.value.language = language
        if (activeLanguage.value === language) activeLanguage.value = 'source'
        await handleUpdateRecord()
    }

    // A person read the AI's title and keeps it: saved as theirs, checked against the current title.
    async function reviewTitle(): Promise<void> {
        const language = activeLanguage.value
        const local = product.value.translations[language]
        const stored = titleStates.value[language]?.title
        if (language === 'source' || !local?.title) return
        product.value.translations = { ...product.value.translations, [language]: { title: local.title, origin: 'manual' } }
        if (stored) titleStates.value = { ...titleStates.value, [language]: { title: { ...stored, origin: 'manual', outdated: false } } }
        await handleUpdateRecord()
    }

    async function translateTitles(languages: string[]): Promise<void> {
        if (!product.value.title || languages.length === 0) return
        translatingTitle.value = true
        try {
            const response = (await translateProductTitle({
                title: product.value.title,
                source_language: product.value.language,
                languages,
                report_item_ids: reportItems.value.map((item) => item.id)
            })) as { data?: { translations?: Record<string, string>; failed?: Record<string, string> } }
            const translated = response.data?.translations ?? {}
            product.value.translations = {
                ...product.value.translations,
                ...Object.fromEntries(Object.entries(translated).map(([language, title]) => [language, { title, origin: 'ai' as const }]))
            }
            titleStates.value = {
                ...titleStates.value,
                ...Object.fromEntries(
                    Object.entries(translated).map(([language, title]) => [
                        language,
                        { title: { value: title, origin: 'ai' as const, version: 0, outdated: false } }
                    ])
                )
            }
            if (Object.keys(response.data?.failed ?? {}).length > 0) {
                window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'warning', loc: 'product.title_not_translated' } }))
            }
            await handleUpdateRecord()
        } catch (error: unknown) {
            notifyServerError(error, 'common.error_saving')
        } finally {
            translatingTitle.value = false
        }
    }

    /** The product as the form has it, for the language check. */
    const productPayload = () => ({
        ...product.value,
        product_type_id: selectedType.value?.id ?? product.value.product_type_id,
        report_items: reportItems.value.map((item) => ({ id: item.id }))
    })

    async function fetchLanguageCheck(language: string | null): Promise<LanguageCheck | null> {
        if (!language || !(selectedType.value?.id ?? product.value.product_type_id)) return null
        try {
            const response = (await checkProductLanguage(productPayload(), language)) as { data?: LanguageCheck }
            return response.data ?? null
        } catch (error: unknown) {
            console.error('Language check failed:', error)
            return null
        }
    }

    // A check answers for one language, product type and set of reports. Once any of them
    // changes, the last answer is neither shown nor acted on: it would name the previous
    // type's templates or the previous tab's outdated translations.
    const checkKey = computed<string>(() =>
        JSON.stringify([renderLanguage.value, selectedType.value?.id ?? null, reportItems.value.map((item) => item.id)])
    )
    const checkIsCurrent = computed<boolean>(() => languageCheck.value?.key === checkKey.value)
    const currentCheck = computed<LanguageCheck | null>(() => (checkIsCurrent.value ? (languageCheck.value?.check ?? null) : null))

    let checkTimer: ReturnType<typeof setTimeout> | undefined

    /** The check for what the form shows now, asked for at once (without waiting for the debounce). */
    async function loadCurrentCheck(): Promise<LanguageCheck | null> {
        clearTimeout(checkTimer)
        if (checkIsCurrent.value) return currentCheck.value
        const key = checkKey.value
        const check = await fetchLanguageCheck(renderLanguage.value)
        if (key === checkKey.value) languageCheck.value = { key, check }
        return check
    }

    watch([visible, checkKey], () => {
        clearTimeout(checkTimer)
        if (visible.value) checkTimer = setTimeout(() => void loadCurrentCheck(), 300)
    })

    watch(publishLanguage, async (language) => {
        publishCheck.value = null
        const check = showPublishConfirmation.value ? await fetchLanguageCheck(language) : null
        if (language === publishLanguage.value) publishCheck.value = check
    })

    /** Outdated translations in the rendered language need a confirmation before preview or download. */
    function needsOutdatedConfirmation(check: LanguageCheck | null, action: () => void): boolean {
        const language = renderLanguage.value
        if (!language || !check?.outdated.length || outdatedConfirmed.value.has(language)) return false
        outdatedCheck.value = check
        pendingOutdatedAction.value = action
        showOutdatedConfirmation.value = true
        return true
    }

    function continueWithOutdated(): void {
        if (renderLanguage.value) outdatedConfirmed.value = new Set([...outdatedConfirmed.value, renderLanguage.value])
        showOutdatedConfirmation.value = false
        const action = pendingOutdatedAction.value
        pendingOutdatedAction.value = null
        action?.()
    }

    function insertProductLink(index: number): void {
        productLinks.value.splice(index, 0, { value: '', value_description: generateLinkKey(takenLinkKeys()) })
    }

    function removeProductLink(index: number): void {
        productLinks.value.splice(index, 1)
        void handleUpdateRecord()
    }

    function moveProductLink(from: number, to: number): void {
        const [moved] = productLinks.value.splice(from, 1)
        if (!moved) return
        productLinks.value.splice(to, 0, moved)
        void handleUpdateRecord()
    }

    // ---- Citing from the description ----
    // The description is the one citing "value" (index 0) of the form.
    const description = {
        get value(): string {
            return product.value.description || ''
        },
        set value(text: unknown) {
            product.value.description = String(text ?? '')
        }
    }
    const {
        setField: setDescriptionField,
        trackSelection: trackDescriptionSelection,
        cite: citeInDescription
    } = useCitingField(
        () => [description],
        () => handleUpdateRecord()
    )

    function onDescriptionBlur(): void {
        trackDescriptionSelection(0)
        void handleUpdateRecord()
    }

    /** Cite a report's link: it becomes one of the product's links (unless it already is), then gets cited. */
    async function citeReportLink(link: ExternalLink): Promise<void> {
        const url = link.url.trim()
        let existing = productLinks.value.find((candidate) => String(candidate.value ?? '').trim() === url)
        if (!existing) {
            existing = { value: url, value_description: generateLinkKey(takenLinkKeys()) }
            productLinks.value.push(existing)
        }
        await citeInDescription(0, String(existing.value_description))
    }

    // Validation rules
    const requiredRule = (value: string | number | null | undefined): true | string => !!value || t('common.required')

    // Computed properties
    const canModify = computed(() => {
        if (!isEditMode.value) return true
        return checkPermission('PUBLISH_UPDATE') && canModifyFlag.value
    })

    const canPublish = computed(() => {
        if (publisherPresets.value.length === 0) return false
        if (!isEditMode.value) return true
        return checkPermission('PUBLISH_PRODUCT') && canAccessFlag.value
    })

    // True when the product's current state is a FINAL state (e.g. published),
    // so newly-added non-final reports will be auto-completed by the backend cascade.
    const productStateIsFinal = computed(() => {
        if (product.value.state_id === undefined || product.value.state_id === null) return false
        return availableStates.value.some((s) => s.id === product.value.state_id && s.state_type === 'final')
    })

    // The full names of the selected publisher presets, used in the publish dialog.
    const selectedPublisherPresetNames = computed<string[]>(() =>
        publisherPresets.value.filter((preset) => preset.selected).map((preset) => preset.name)
    )
    const FIRST_STRONG_ISOLATE = '\u2068'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'
    const isolateAuto = (value: string): string => `${FIRST_STRONG_ISOLATE}${value}${POP_DIRECTIONAL_ISOLATE}`
    const selectedPublisherPresetList = computed(() =>
        formatList(selectedPublisherPresetNames.value.map(isolateAuto), { style: 'long', type: 'conjunction' })
    )

    const showPublicWebSelection = computed(() => publicWebOptions.value.length > 1)

    // Methods
    function resetForm() {
        product.value = {
            id: -1,
            title: '',
            description: '',
            product_type_id: undefined,
            state_id: undefined,
            report_items: [],
            public_web_ids: [],
            links: [],
            // Written in the user's default language unless they pick another one.
            language: defaultContentLanguage.value,
            translations: {},
            tag_ids: []
        }
        resetLanguages()
        productLinks.value = []
        selectedType.value = null
        isEditMode.value = false
        showError.value = false
        canModifyFlag.value = false
        canAccessFlag.value = false
        reportItems.value = []
        normalizePublicWebSelection()
        formRef.value?.reset?.()
        resetPublisherPresets()
        selectDefaultState()
        initialFormState.value = snapshotForm()
    }

    function normalizePublicWebIds(ids: Array<number | string> | undefined | null): Array<number | string> {
        if (!Array.isArray(ids)) {
            return []
        }

        return Array.from(new Set(ids.map((id) => Number(id)).filter((id) => Number.isFinite(id))))
    }

    function normalizePublicWebSelection() {
        // Without options the valid-id set is empty, so filtering here would
        // silently wipe the product's saved targeting (e.g. after a failed
        // options fetch). Leave the stored selection alone instead.
        if (publicWebOptions.value.length === 0) {
            return
        }

        const validIds = new Set(normalizePublicWebIds(publicWebOptions.value.map((web) => web.id)))
        const selectedIds = normalizePublicWebIds(product.value.public_web_ids)

        product.value.public_web_ids = selectedIds.filter((id) => validIds.has(Number(id)))

        // Keep legacy behavior visible in UI: no explicit mapping means all websites.
        if (showPublicWebSelection.value && product.value.public_web_ids.length === 0) {
            product.value.public_web_ids = publicWebOptions.value.map((web) => web.id)
        }
    }

    function resetPublisherPresets() {
        publisherPresets.value.forEach((preset) => {
            preset.selected = false
        })
    }

    function snapshotForm() {
        return JSON.stringify({
            product: product.value,
            links: productLinks.value,
            selectedType: selectedType.value,
            reportItems: reportItems.value,
            publisherPresets: publisherPresets.value.map((p) => ({ id: p.id, selected: p.selected }))
        })
    }

    function hasUnsavedChanges() {
        if (initialFormState.value === null) return false
        return snapshotForm() !== initialFormState.value
    }

    /**
     * Saving a product in a FINAL state (e.g. published) completes its reports on the server -
     * whether the state was just set or reports were just added. Show the states they have now.
     */
    async function refreshReportItemStates(): Promise<void> {
        if (product.value.id === -1 || !productStateIsFinal.value || reportItems.value.length === 0) return

        try {
            const response = await getProductById(product.value.id)
            const stored = new Map(((response.data?.report_items || []) as ReportItem[]).map((item) => [String(item.id), item] as const))
            // The new states are the server's, not an edit: keep a pristine form pristine.
            const wasPristine = !hasUnsavedChanges()
            reportItems.value = reportItems.value.map((item) => {
                const current = stored.get(String(item.id))
                return current ? { ...item, state: current['state'], state_id: current['state_id'] } : item
            })
            if (wasPristine) {
                initialFormState.value = snapshotForm()
            }
        } catch (error: unknown) {
            console.error('Failed to refresh the states of the report items:', error)
        }
    }

    function selectDefaultState() {
        if (!availableStates.value || availableStates.value.length === 0) return
        const defaultState = availableStates.value.find((state) => state.is_default)
        if (defaultState) {
            product.value.state_id = defaultState.id
        }
    }

    function handleProductTypeChange(): void {
        if (selectedType.value) {
            product.value.product_type_id = selectedType.value.id
            handleUpdateRecord()
        }
    }

    async function prepareProduct(): Promise<boolean> {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return false

        showError.value = false
        product.value.product_type_id = selectedType.value?.id
        product.value.report_items = reportItems.value.map((item) => ({ id: item.id }))
        product.value.public_web_ids = normalizePublicWebIds(product.value.public_web_ids)
        product.value.links = productLinks.value
            .map((link) => ({ key: String(link.value_description ?? ''), url: String(link.value ?? '').trim() }))
            .filter((link) => link.url)
        return true
    }

    async function handlePublicWebSelectionChange(): Promise<void> {
        await nextTick()
        if (isEditMode.value && product.value.id !== -1) {
            await handleUpdateRecord()
        }
    }

    function openReportItemSelector(): void {
        reportItemSelector.value?.openSelector?.()
    }

    async function handleReportItemsChanged(items: ReportItem[]): Promise<void> {
        reportItems.value = Array.isArray(items) ? [...items] : []

        if (isEditMode.value && product.value.id !== -1) {
            await handleUpdateRecord()
        }
    }

    function getSelectedPublisherIds(): never[] {
        return publisherPresets.value.filter((preset) => preset.selected).map((preset) => preset.id) as unknown as never[]
    }

    function validatePublisherSelection(): boolean {
        const selectedIds = getSelectedPublisherIds()
        if (selectedIds.length === 0) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.no_publisher_selected' }
                })
            )
            return false
        }
        return true
    }

    async function handleSave(): Promise<boolean> {
        if (!(await prepareProduct())) return false

        try {
            if (product.value.id === -1) {
                const response = await createProduct(product.value)
                product.value.id = response.data
                // The server sets a new product's language from the author's settings.
                try {
                    const created = await getProductById(product.value.id)
                    product.value.language = (created.data as ProductDetailPayload | undefined)?.language ?? product.value.language
                } catch (error: unknown) {
                    console.error('Failed to read the new product back:', error)
                }
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'product.created_successfully' }
                    })
                )
            } else {
                await updateProduct(product.value)
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'product.updated_successfully' }
                    })
                )
            }
            window.dispatchEvent(new CustomEvent('product-updated'))
            initialFormState.value = snapshotForm()
            await refreshReportItemStates()
            return true
        } catch (error: unknown) {
            showError.value = true
            notifyServerError(error, 'product.error')
            return false
        }
    }

    // Saved with the product: right away once it exists, with the product when it is created.
    function changeTags(tagIds: number[]): void {
        product.value.tag_ids = tagIds
        void handleUpdateRecord()
    }

    function handleStateChange(newStateId: number | string | null): void {
        // StateSelector is bound one-way via :model-value, so we must write the
        // selected id back into the product before persisting.
        product.value.state_id = newStateId ?? undefined
        handleUpdateRecord()
    }

    async function handleUpdateRecord(): Promise<void> {
        if (!isEditMode.value || product.value.id === -1) return

        if (!(await prepareProduct())) return

        try {
            await updateProduct(product.value)
            window.dispatchEvent(new CustomEvent('product-updated'))
            initialFormState.value = snapshotForm()
        } catch {
            showError.value = true
            return
        }
        await refreshReportItemStates()
    }

    function handleCancel(): void {
        if (!isEditMode.value && hasUnsavedChanges()) {
            showCloseConfirmation.value = true
            return
        }
        closeDialog()
    }

    function confirmClose(): void {
        showCloseConfirmation.value = false
        closeDialog()
    }

    async function saveAndClose(): Promise<void> {
        showCloseConfirmation.value = false
        const saved = await handleSave()
        if (saved) {
            closeDialog()
        }
    }

    function closeDialog(): void {
        visible.value = false
    }

    async function handlePublishConfirmation(): Promise<void> {
        if (!validatePublisherSelection()) return

        const language = renderLanguage.value
        publishLanguage.value = language
        publishCheck.value = currentCheck.value
        if (!isEditMode.value && hasUnsavedChanges()) {
            showPublishUnsavedConfirmation.value = true
        } else {
            showPublishConfirmation.value = true
        }
        // The open tab's check is still on its way: the dialog lists it once it arrives.
        if (!checkIsCurrent.value) {
            const check = await loadCurrentCheck()
            if (publishLanguage.value === language) publishCheck.value = check
        }
    }

    async function handlePublish(): Promise<void> {
        showPublishConfirmation.value = false

        if (!(await prepareProduct())) return

        const selectedPublisherIds: any = getSelectedPublisherIds()

        try {
            const response = await publishProduct(product.value, selectedPublisherIds, publishLanguage.value)
            if (response.data.overall_success) {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'success', loc: 'product.publish_successful' }
                    })
                )
            } else {
                window.dispatchEvent(
                    new CustomEvent('notification', {
                        detail: { type: 'error', loc: 'product.publish_failed' }
                    })
                )
            }
        } catch {
            showError.value = true
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.publish_error' }
                })
            )
        }
    }

    async function saveAndPublish(): Promise<void> {
        showPublishUnsavedConfirmation.value = false
        const saved = await handleSave()
        if (saved) {
            isEditMode.value = true
            canModifyFlag.value = true
            canAccessFlag.value = true
            showPublishConfirmation.value = true
        }
    }

    function publishOnly(): void {
        showPublishUnsavedConfirmation.value = false
        handlePublish()
    }

    async function handlePreview(event?: MouseEvent): Promise<void> {
        if (needsOutdatedConfirmation(currentCheck.value, () => void handlePreview(event))) return
        // Reserve the tab before validation or the API request yields. Waiting
        // until either promise resolves loses browser user activation and may
        // cause the preview to be blocked as an unsolicited popup.
        const previewWindow = openBlankTabWithoutOpener()
        const ctrl = Boolean(event?.ctrlKey || event?.metaKey)

        try {
            // The tab, type or reports just changed and their check is still on its way.
            if (!checkIsCurrent.value && needsOutdatedConfirmation(await loadCurrentCheck(), () => void handlePreview(event))) {
                previewWindow?.close()
                return
            }
            if (!(await prepareProduct())) {
                previewWindow?.close()
                return
            }

            const response = await previewProduct(product.value, ctrl, authStore.jwt, renderLanguage.value)
            const token = response.data.token

            const apiBase = import.meta.env.VITE_APP_TARANIS_NG_CORE_API || '/api/v1'
            const previewUrl = `${apiBase}/publish/products/preview/${token}`
            navigateReservedTabOrCurrentWindow(previewWindow, previewUrl)
        } catch (error: unknown) {
            previewWindow?.close()
            console.error('Preview failed:', error)
            showError.value = true
        }
    }

    async function handleDownload(event?: MouseEvent): Promise<void> {
        if (needsOutdatedConfirmation(await loadCurrentCheck(), () => void handleDownload(event))) return
        const ctrl = Boolean(event?.ctrlKey || event?.metaKey)

        if (!(await prepareProduct())) return

        try {
            const response = await previewProduct(product.value, ctrl, authStore.jwt, renderLanguage.value)
            const downloaded = await ApiService.download(
                `/publish/products/preview/${response.data.token}`,
                undefined,
                product.value.title || 'product',
                'GET'
            )
            if (!downloaded) showError.value = true
        } catch (error: unknown) {
            console.error('Download failed:', error)
            showError.value = true
        }
    }

    async function loadAvailableStates() {
        try {
            const response = await getEntityTypeStates('product')
            availableStates.value = response.data.states || []
            selectDefaultState()
        } catch (error: unknown) {
            console.error('Failed to load available states for PRODUCT:', error)
            availableStates.value = []
        }
    }

    async function loadProductTypes() {
        try {
            const response = await getAllUserProductTypes()
            productTypes.value = response.data.items || []
        } catch (error: unknown) {
            console.error('Failed to load product types:', error)
        }
    }

    async function loadPublisherPresets() {
        try {
            const response = await getAllUserPublishersPresets()
            publisherPresets.value = (response.data.items || []).map((preset) => ({
                ...preset,
                selected: false
            }))
        } catch (error: unknown) {
            console.error('Failed to load publisher presets:', error)
        }
    }

    async function loadPublicWebOptions() {
        // The store fetches the publish-scoped list once and caches it; a failed
        // fetch must not touch the product's saved targeting below.
        const wasPristine = !hasUnsavedChanges()
        await publishStore.loadPublicWebOptions()
        normalizePublicWebSelection()
        // When this call actually refilled emptied options, the normalization above
        // can adjust the targeting (stale ids dropped, the legacy "no mapping means
        // all webs" made explicit). On a form the user has not touched yet that is
        // our own adjustment, not their edit, so re-baseline the unsaved-changes
        // snapshot rather than warning them about a change they did not make.
        if (wasPristine && initialFormState.value !== null) {
            initialFormState.value = snapshotForm()
        }
    }

    // Public methods for opening dialog
    function openDialog(): void {
        visible.value = true
        resetForm()
        // Cheap when the options are already cached; it only re-requests after an
        // invalidation (a web created or deleted elsewhere), so the target
        // selector cannot go missing on a dialog opened later in the same view.
        void loadPublicWebOptions()
    }

    function openEditDialog(data: ProductEditPayload | ProductDetailPayload, editMeta?: { modify: boolean; access: boolean }): void {
        visible.value = true
        isEditMode.value = true
        canModifyFlag.value = editMeta?.modify ?? (data as ProductEditPayload).modify ?? true
        canAccessFlag.value = editMeta?.access ?? (data as ProductEditPayload).access ?? true
        showError.value = false

        product.value = {
            id: data.id,
            title: data.title,
            description: data.description || '',
            product_type_id: data.product_type_id,
            state_id: data.state_id,
            report_items: data.report_items || [],
            public_web_ids: normalizePublicWebIds(data.public_web_ids),
            links: data.links || [],
            language: (data as ProductDetailPayload).language ?? null,
            translations: Object.fromEntries(
                Object.entries((data as ProductDetailPayload).translations ?? {})
                    .filter(([, state]) => state.title?.value)
                    .map(([language, state]) => [language, { title: String(state.title?.value), origin: state.title?.origin ?? 'manual' }])
            ),
            tag_ids: (data as ProductDetailPayload).tags ?? []
        }
        resetLanguages()
        titleStates.value = (data as ProductDetailPayload).translations ?? {}
        productLinks.value = toLinkValues(data.links)

        reportItems.value = Array.isArray(data.report_items) ? [...data.report_items] : []
        selectedType.value = productTypes.value.find((type) => type.id === data.product_type_id) || null
        normalizePublicWebSelection()
        initialFormState.value = snapshotForm()
        // See openDialog: refills the options after an invalidation. It runs after
        // the product is in place, so its own normalizePublicWebSelection() call
        // reconciles the loaded targeting against the freshly fetched options.
        void loadPublicWebOptions()
    }

    // Event listeners
    const handleNewProduct = (event: Event): void => {
        const data = (event as CustomEvent<unknown>).detail
        openDialog()
        if (data && Array.isArray(data)) {
            reportItems.value = [...(data as ReportItem[])]
        }
    }

    const handleShowProductEdit = async (event: Event): Promise<void> => {
        const data = (event as CustomEvent<unknown>).detail
        if (!data || typeof data !== 'object') {
            return
        }

        const editData = data as ProductEditPayload

        try {
            const response = await getProductById(editData.id)
            openEditDialog(response.data as ProductDetailPayload, { modify: editData.modify, access: editData.access })
        } catch (error: unknown) {
            console.error('Failed to load product detail:', error)
            // Fallback keeps previous behavior if detail endpoint fails.
            openEditDialog(editData)
        }
    }

    onMounted(() => {
        void tagsStore.load('product')
        loadAvailableStates()
        loadProductTypes()
        loadPublisherPresets()
        loadPublicWebOptions()
        window.addEventListener('new-product', handleNewProduct)
        window.addEventListener('show-product-edit', handleShowProductEdit)
    })

    onUnmounted(() => {
        window.removeEventListener('new-product', handleNewProduct)
        window.removeEventListener('show-product-edit', handleShowProductEdit)
    })

    // Expose methods for parent components
    defineExpose({
        openDialog,
        openEditDialog,
        handlePreview
    })
</script>

<style scoped>
    .v-toolbar :deep(.v-select) {
        margin-top: 8px;
    }

    /* Keep the unsaved-changes dialog button labels white regardless of theme on-* colors. */
    .confirm-btn,
    .confirm-btn :deep(.v-btn__content) {
        color: #fff !important;
    }
</style>
