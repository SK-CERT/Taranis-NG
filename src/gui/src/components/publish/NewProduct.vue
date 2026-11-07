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
                    keypath="product.publish_confirmation_product_preset"
                >
                    <template #productPreset>
                        <bdi dir="auto">{{ selectedProductPreset?.name || $t('product.no_product_preset') }}</bdi>
                    </template>
                </i18n-t>
            </div>
            <div class="mb-1">
                <i18n-t
                    scope="global"
                    keypath="product.publish_confirmation_deliveries"
                >
                    <template #deliveries>
                        <ul class="publish-deliveries">
                            <li
                                v-for="delivery in tickedDeliveries"
                                :key="delivery.id"
                            >
                                <bdi dir="auto">{{ deliveryLabel(delivery) }}</bdi>
                            </li>
                        </ul>
                    </template>
                </i18n-t>
            </div>
            <!-- What rendering falls back on, for each language the ticked deliveries send. -->
            <ProductLanguageNotices
                v-for="entry in publishChecks"
                :key="entry.language"
                class="mt-3"
                :check="entry.check"
                :language="entry.language"
            />
            <div class="text-body-2 text-grey mt-3">
                {{ $t('product.publish_confirmation_message') }}
            </div>
        </ConfirmationDialog>

        <ConfirmationDialog
            v-model="confirmOverwrite"
            title-key="report_item.translation.overwrite_title"
            confirm-label-key="report_item.translation.overwrite_confirm"
            :message="t('report_item.translation.overwrite_message')"
            max-width="500px"
            @confirm="runPendingField"
        />

        <ConfirmationDialog
            v-model="showOutdatedConfirmation"
            title-key="product.outdated_confirmation"
            confirm-label-key="product.outdated_continue"
            max-width="500px"
            @confirm="continueWithOutdated"
        >
            <ProductLanguageNotices
                :check="outdatedCheck ? { ...outdatedCheck, missing: [], formats: [] } : null"
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
                    :translating="translationJob.running"
                    @translate-all="translateAll"
                />
                <div
                    v-if="translationJob.running"
                    class="pb-3"
                    data-test="product-translation-progress"
                >
                    <v-progress-linear
                        :model-value="translationJob.total ? (100 * translationJob.done) / translationJob.total : 0"
                        color="primary"
                        height="6"
                        rounded
                    />
                    <span class="text-caption">{{
                        t('report_item.translation.progress', { done: translationJob.done, total: translationJob.total })
                    }}</span>
                </div>
                <div
                    v-if="activeLanguage !== 'source'"
                    class="d-flex align-center flex-wrap ga-2 mb-3"
                    data-test="product-translation-header"
                >
                    <span class="text-body-2 text-medium-emphasis">
                        {{ t('product.translation_intro', { language: languageName(activeLanguage) }) }}
                    </span>
                    <v-spacer />
                    <v-btn
                        v-if="canModify && unreviewedFields.length > 0"
                        color="success"
                        variant="tonal"
                        prepend-icon="mdi-check-all"
                        :disabled="translationBusy"
                        data-test="review-product-language"
                        @click="reviewLanguage"
                    >
                        {{ t('report_item.translation.review_all') }}
                    </v-btn>
                    <v-btn
                        v-if="canModify && product.language"
                        color="primary"
                        variant="tonal"
                        prepend-icon="mdi-translate"
                        :loading="translatingKey === 'language'"
                        :disabled="translationBusy"
                        data-test="translate-product-language"
                        @click="translateLanguage"
                    >
                        {{ t('report_item.translation.translate_language', { language: languageName(activeLanguage) }) }}
                    </v-btn>
                </div>
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
                            <v-select
                                v-model="selectedProductPreset"
                                dir="auto"
                                :items="productPresets"
                                item-title="name"
                                item-value="id"
                                :label="$t('product.product_preset')"
                                :rules="[requiredRule]"
                                :disabled="!canModify"
                                return-object
                                @update:model-value="handleProductPresetChange"
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
                                        :state="fieldState(activeLanguage, 'title')"
                                        :reviewable="canModify"
                                        @review="reviewField('title')"
                                    />
                                    <v-btn
                                        v-if="canModify && product.title"
                                        icon="mdi-translate"
                                        variant="text"
                                        density="compact"
                                        size="small"
                                        tabindex="-1"
                                        :loading="translatingKey === 'title'"
                                        :disabled="translationBusy"
                                        :title="$t('report_item.translation.translate_field')"
                                        data-test="translate-product-title"
                                        @mousedown.stop
                                        @click.stop="translateField('title')"
                                    />
                                </template>
                            </v-text-field>
                        </v-col>
                        <v-col cols="12">
                            <v-textarea
                                :ref="(field) => setDescriptionField(0, field)"
                                v-model="descriptionModel"
                                dir="auto"
                                :spellcheck="spellcheck"
                                :label="$t('product.description')"
                                :hint="activeLanguage === 'source' ? '' : product.description"
                                :persistent-hint="activeLanguage !== 'source'"
                                :disabled="!canModify"
                                rows="3"
                                data-test="product-description"
                                @blur="onDescriptionBlur"
                                @keyup="trackDescriptionSelection(0)"
                                @click="trackDescriptionSelection(0)"
                            >
                                <template #append-inner>
                                    <template v-if="activeLanguage !== 'source'">
                                        <TranslationState
                                            :state="fieldState(activeLanguage, 'description')"
                                            :reviewable="canModify"
                                            @review="reviewField('description')"
                                        />
                                        <v-btn
                                            v-if="canModify && product.description"
                                            icon="mdi-translate"
                                            variant="text"
                                            density="compact"
                                            size="small"
                                            tabindex="-1"
                                            :loading="translatingKey === 'description'"
                                            :disabled="translationBusy"
                                            :title="$t('report_item.translation.translate_field')"
                                            data-test="translate-product-description"
                                            @mousedown.stop
                                            @click.stop="translateField('description')"
                                        />
                                    </template>
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
                                :text="descriptionModel"
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

                    <!-- Where publishing sends the product: the product preset's deliveries -->
                    <v-row v-if="selectedProductPreset">
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <div class="text-title-medium mb-2">
                                {{ $t('product.deliveries') }}
                            </div>
                            <div v-if="channelDeliveries.length > 0">
                                <v-checkbox
                                    v-for="delivery in channelDeliveries"
                                    :key="delivery.id"
                                    v-model="tickedDeliveryIds"
                                    :value="delivery.id"
                                    :disabled="!canPublish"
                                    hide-details
                                    density="compact"
                                >
                                    <template #label>
                                        <bdi dir="auto">{{ deliveryLabel(delivery) }}</bdi>
                                    </template>
                                </v-checkbox>
                            </div>
                            <div
                                v-else
                                class="text-body-2 text-medium-emphasis py-2"
                            >
                                {{ $t('product.no_channels') }}
                            </div>
                        </v-col>
                        <!-- Of the product preset's webs, those it appears on; none keeps it off the public web. -->
                        <v-col
                            v-if="webChoices.length > 0"
                            cols="12"
                            md="6"
                            data-test="product-webs"
                        >
                            <div class="text-title-medium mb-2">
                                {{ $t('product.public_web_targets') }}
                            </div>
                            <v-checkbox
                                v-for="web in webChoices"
                                :key="web.id"
                                v-model="shownWebIds"
                                :value="web.id"
                                :disabled="!canModify"
                                hide-details
                                density="compact"
                            >
                                <template #label>
                                    <bdi dir="auto">{{ web.name }}</bdi>
                                </template>
                            </v-checkbox>
                        </v-col>
                        <v-col
                            v-else-if="publicWebNote"
                            cols="12"
                            md="6"
                            class="text-body-2 text-medium-emphasis"
                        >
                            {{ publicWebNote }}
                        </v-col>
                    </v-row>

                    <!-- Action Buttons -->
                    <v-row class="mt-4">
                        <v-col
                            cols="12"
                            md="6"
                        >
                            <!-- A product preset with several formats previews the one picked. -->
                            <v-menu v-if="formats.length > 1">
                                <template #activator="{ props: menuProps }">
                                    <v-btn
                                        v-bind="menuProps"
                                        :prepend-icon="ICONS.READ_OUTLINE"
                                        append-icon="mdi-menu-down"
                                        color="primary"
                                        variant="flat"
                                    >
                                        {{ $t('product.preview') }}
                                    </v-btn>
                                </template>
                                <v-list
                                    density="compact"
                                    data-test="preview-formats"
                                >
                                    <v-list-item
                                        v-for="format in formats"
                                        :key="format.id"
                                        @click="(event: MouseEvent) => handlePreview(event, format.id)"
                                    >
                                        <v-list-item-title>
                                            <bdi dir="auto">{{ format.title }}</bdi>
                                        </v-list-item-title>
                                    </v-list-item>
                                </v-list>
                            </v-menu>
                            <v-btn
                                v-else
                                :prepend-icon="ICONS.READ_OUTLINE"
                                :disabled="selectedProductPreset !== null && formats.length === 0"
                                color="primary"
                                variant="flat"
                                @click="handlePreview"
                            >
                                {{ $t('product.preview') }}
                            </v-btn>
                            <v-menu v-if="formats.length > 1">
                                <template #activator="{ props: menuProps }">
                                    <v-btn
                                        v-bind="menuProps"
                                        class="ms-2"
                                        :prepend-icon="ICONS.DOWNLOAD"
                                        append-icon="mdi-menu-down"
                                        color="primary"
                                        variant="flat"
                                    >
                                        {{ $t('common.download') }}
                                    </v-btn>
                                </template>
                                <v-list
                                    density="compact"
                                    data-test="download-formats"
                                >
                                    <v-list-item
                                        v-for="format in formats"
                                        :key="format.id"
                                        @click="(event: MouseEvent) => handleDownload(event, format.id)"
                                    >
                                        <v-list-item-title>
                                            <bdi dir="auto">{{ format.title }}</bdi>
                                        </v-list-item-title>
                                    </v-list-item>
                                </v-list>
                            </v-menu>
                            <v-btn
                                v-else
                                class="ms-2"
                                :prepend-icon="ICONS.DOWNLOAD"
                                :disabled="selectedProductPreset !== null && formats.length === 0"
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
    import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuthStore } from '@/stores/auth'
    import ApiService from '@/services/api_service'
    import { ICONS } from '@/config/ui-constants'
    import {
        createProduct,
        updateProduct,
        publishProduct,
        previewProduct,
        getProductById,
        translateProduct,
        checkProductLanguage
    } from '@/api/publish'
    import { getReportItem } from '@/api/analyze'
    import { getAllUserProductPresets } from '@/api/user'
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

    // The texts of a product that are translated.
    const PRODUCT_FIELDS = ['title', 'description'] as const
    type ProductField = (typeof PRODUCT_FIELDS)[number]
    // Written by the AI (until a person edits or reviews it), reviewed by a person, or a person's own.
    type FieldTranslation = { value: string; origin: 'ai' | 'reviewed' | 'manual' }

    type ProductModel = {
        id: number
        title: string
        description: string
        product_preset_id: number | undefined
        state_id: number | string | undefined
        report_items: Array<{ id: number | string }>
        links: ProductLink[]
        // The language the product is written in; null while not set.
        language: string | null
        // Its title and description in other languages, saved with the product.
        translations: Record<string, Partial<Record<ProductField, FieldTranslation>>>
        // The tags people put on it, saved with the product.
        tag_ids: number[]
        // Of its product preset's webs, those it is limited to; none: every one. Undefined until
        // known, so that saving then keeps the stored ones.
        public_web_ids?: number[] | undefined
        // Off, it stays off the public web; undefined until known, like the webs.
        public_web_enabled?: boolean | undefined
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

    /** The product in a language and a format, and the channel it goes to (none: preview only). */
    type Delivery = {
        id: number
        // None: the language the product is written in.
        language: string | null
        product_format_id: number
        product_format_title: string
        publishing_channel_id: string | null
        publishing_channel_name: string | null
    }

    /** What the product is published as. */
    type ProductPreset = {
        id: number
        name: string
        deliveries: Delivery[]
        public_web_enabled: boolean
        public_web_names?: string[]
        // The webs a product of it can be shown on: its own, else every web.
        web_choices?: Array<{ id: number; name: string }>
    }

    type PublishResult = {
        delivery_id: number
        success: boolean
    }

    type AvailableState = {
        id: number | string
        title?: string
        is_default?: boolean
        state_type?: string
        [key: string]: unknown
    }

    type ProductEditPayload = {
        id: number
        title: string
        description: string
        product_preset_id: number | undefined
        state_id: number | string | undefined
        report_items?: ReportItem[]
        links?: ProductLink[]
        modify: boolean
        access: boolean
    }

    type ProductDetailPayload = {
        id: number
        title: string
        description?: string
        product_preset_id: number | undefined
        state_id: number | string | undefined
        report_items?: ReportItem[]
        links?: ProductLink[]
        language?: string | null
        translations?: Record<string, Partial<Record<ProductField, TranslationStateValue>>>
        tags?: number[]
        public_web_ids?: number[]
        public_web_enabled?: boolean
    }

    const { t } = useI18n()
    const { formatList } = useLocaleFormatters()
    const tagsStore = useTagsStore()
    const spellcheck = useSpellcheck()
    const { checkPermission } = useAuth()
    const authStore = useAuthStore()

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
        product_preset_id: undefined,
        state_id: undefined,
        report_items: [],
        links: [],
        language: null,
        translations: {},
        tag_ids: [],
        public_web_ids: [],
        public_web_enabled: true
    })

    const selectedProductPreset = ref<ProductPreset | null>(null)
    const reportItems = ref<ReportItem[]>([])
    const productPresets = ref<ProductPreset[]>([])
    // The deliveries Publish sends to; all of the product preset's channels unless unticked.
    const tickedDeliveryIds = ref<number[]>([])
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

    // Citations of the description and of its translations, so a link still cited cannot be removed.
    const productCitationCount = (key: string): number =>
        [product.value.description, ...Object.values(product.value.translations).map((texts) => texts.description?.value)]
            .flatMap((text) => citedKeys(text ?? ''))
            .filter((cited) => cited === key).length

    const reportLinkGroups = computed(() =>
        reportItems.value
            .filter((item) => (item.links || []).length > 0)
            .map((item) => ({ title: String(item.title || item.id), links: (item.links || []) as ExternalLink[] }))
    )

    // ---- Languages ----
    // The open tab is the language the product is previewed, downloaded and published in.
    const { languageName, defaultContentLanguage } = useContentLanguages()
    const activeLanguage = ref<string>('source')
    // The translations as last stored, for their state (who wrote them, outdated or not), each with
    // the original it was checked against: core's when loaded, the form's when the AI made it or a
    // person reviewed it here.
    type StoredTranslation = TranslationStateValue & { original: string }
    const storedTranslations = ref<Record<string, Partial<Record<ProductField, StoredTranslation>>>>({})
    // What the AI is translating for the open tab: its language, or one of its texts.
    const translatingKey = ref<'language' | ProductField | null>(null)
    // "Translate whole product": one language after another, each saved when it is done.
    const translationJob = reactive({ running: false, done: 0, total: 0 })
    const translationBusy = computed(() => translationJob.running || translatingKey.value !== null)
    const confirmOverwrite = ref<boolean>(false)
    const pendingField = ref<ProductField | null>(null)
    // The last language check, with what it was made for (see checkKey).
    const languageCheck = ref<{ key: string; check: LanguageCheck | null } | null>(null)
    // The checks of the languages Publish sends, for the confirmation.
    const publishChecks = ref<Array<{ language: string; check: LanguageCheck | null }>>([])
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
    const sourceText = (field: ProductField): string => String(product.value[field] ?? '')

    // A text's translation as the form has it: typed by a person, it is no longer the AI's, nor
    // outdated. Otherwise it is outdated as core found it, or once its original changes here, as
    // core will see it when that is saved.
    const fieldState = (language: string, field: ProductField): TranslationStateValue | null => {
        const local = product.value.translations[language]?.[field]
        if (!local?.value) return null
        const stored = storedTranslations.value[language]?.[field]
        if (!stored) return { value: local.value, origin: local.origin, version: 0, outdated: false }
        const outdated = (stored.outdated || sourceText(field) !== stored.original) && local.value === stored.value
        return { ...stored, value: local.value, origin: local.origin, outdated }
    }

    // Each tab's translation status: the title, and the description when there is one.
    const tabStatuses = computed<Record<string, string>>(() =>
        Object.fromEntries(
            productLanguages.value.map((language) => [
                language,
                translationStatus(
                    PRODUCT_FIELDS.filter((field) => sourceText(field)).map((field) => ({
                        original: sourceText(field),
                        row: fieldState(language, field)
                    }))
                )
            ])
        )
    )
    const renderLanguage = computed<string | null>(() => (activeLanguage.value === 'source' ? product.value.language : activeLanguage.value))

    const setTranslation = (language: string, field: ProductField, text: FieldTranslation): void => {
        product.value.translations = { ...product.value.translations, [language]: { ...product.value.translations[language], [field]: text } }
    }

    // Checked against the current original: the AI translated it, or a person reviewed it.
    const setStored = (language: string, field: ProductField, state: TranslationStateValue): void => {
        const checked = { ...state, original: sourceText(field) }
        storedTranslations.value = { ...storedTranslations.value, [language]: { ...storedTranslations.value[language], [field]: checked } }
    }

    // The open tab's text: the original, or its translation (typed by a person: no longer the AI's).
    const textModel = (field: ProductField) =>
        computed<string>({
            get: () =>
                activeLanguage.value === 'source'
                    ? sourceText(field)
                    : (product.value.translations[activeLanguage.value]?.[field]?.value ?? ''),
            set: (value: string) => {
                if (activeLanguage.value === 'source') product.value[field] = value
                else setTranslation(activeLanguage.value, field, { value, origin: 'manual' })
            }
        })
    const titleModel = textModel('title')
    const descriptionModel = textModel('description')

    function resetLanguages(): void {
        activeLanguage.value = 'source'
        storedTranslations.value = {}
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
        if (Object.values(product.value.translations[language] ?? {}).some((text) => text?.value)) {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'product.language_in_use' } }))
            return
        }
        product.value.language = language
        if (activeLanguage.value === language) activeLanguage.value = 'source'
        await handleUpdateRecord()
    }

    const notify = (type: 'success' | 'info' | 'warning', loc: string, params?: Record<string, unknown>): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc, ...(params ? { params } : {}) } }))
    }

    // The AI translations of the open tab nobody has edited or reviewed yet.
    const unreviewedFields = computed<ProductField[]>(() =>
        activeLanguage.value === 'source'
            ? []
            : PRODUCT_FIELDS.filter((field) => sourceText(field) && fieldState(activeLanguage.value, field)?.origin === 'ai')
    )

    // A person read the AI's text and keeps it: still the AI's, but reviewed and checked against the current original.
    const markReviewed = (language: string, field: ProductField): void => {
        const local = product.value.translations[language]?.[field]
        if (!local?.value) return
        setTranslation(language, field, { value: local.value, origin: 'reviewed' })
        const stored = storedTranslations.value[language]?.[field]
        if (stored) setStored(language, field, { ...stored, origin: 'reviewed', outdated: false })
    }

    async function reviewField(field: ProductField): Promise<void> {
        if (activeLanguage.value === 'source') return
        markReviewed(activeLanguage.value, field)
        await handleUpdateRecord()
    }

    async function reviewLanguage(): Promise<void> {
        const fields = [...unreviewedFields.value]
        if (fields.length === 0) return
        for (const field of fields) markReviewed(activeLanguage.value, field)
        await handleUpdateRecord()
        notify('success', 'report_item.translation.reviewed', { count: fields.length })
    }

    // What the AI fills: texts with no translation, or an outdated one the AI made.
    const fieldsToFill = (language: string): ProductField[] =>
        PRODUCT_FIELDS.filter((field) => {
            if (!sourceText(field).trim()) return false
            const state = fieldState(language, field)
            return !state || (state.outdated && state.origin === 'ai')
        })

    // Puts the AI's translations of `fields` into `language` in the form; true when some failed.
    async function translateInto(language: string, fields: ProductField[]): Promise<boolean> {
        const response = (await translateProduct({
            texts: Object.fromEntries(fields.map((field) => [field, sourceText(field)])),
            source_language: product.value.language,
            languages: [language],
            report_item_ids: reportItems.value.map((item) => item.id)
        })) as { data?: { translations?: Record<string, Partial<Record<ProductField, string>>>; failed?: Record<string, unknown> } }
        const texts = response.data?.translations?.[language] ?? {}
        for (const field of PRODUCT_FIELDS) {
            const value = texts[field]
            if (!value) continue
            setTranslation(language, field, { value, origin: 'ai' })
            setStored(language, field, { value, origin: 'ai', version: 0, outdated: false })
        }
        return Object.keys(response.data?.failed ?? {}).length > 0
    }

    // "Translate whole product": what is missing or outdated, language after language.
    async function translateAll(): Promise<void> {
        const languages = productLanguages.value.filter((language) => fieldsToFill(language).length > 0)
        if (languages.length === 0) {
            notify('info', 'product.nothing_to_translate')
            return
        }
        Object.assign(translationJob, { running: true, done: 0, total: languages.length })
        let failed = false
        try {
            for (const language of languages) {
                failed = (await translateInto(language, fieldsToFill(language))) || failed
                await handleUpdateRecord()
                translationJob.done++
            }
            if (failed) notify('warning', 'product.texts_not_translated')
            else notify('success', 'report_item.translation.finished')
        } catch (error: unknown) {
            notifyServerError(error, 'common.error_saving')
        } finally {
            translationJob.running = false
        }
    }

    async function translateInTab(key: 'language' | ProductField, fields: ProductField[]): Promise<void> {
        translatingKey.value = key
        try {
            if (await translateInto(activeLanguage.value, fields)) notify('warning', 'product.texts_not_translated')
            await handleUpdateRecord()
        } catch (error: unknown) {
            notifyServerError(error, 'common.error_saving')
        } finally {
            translatingKey.value = null
        }
    }

    // "Translate into {language}": what is missing or outdated in the open tab.
    async function translateLanguage(): Promise<void> {
        const fields = fieldsToFill(activeLanguage.value)
        if (fields.length === 0) {
            notify('info', 'product.nothing_to_translate')
            return
        }
        await translateInTab('language', fields)
    }

    // One text into the open tab's language; a translation a person wrote or reviewed is replaced only after asking.
    function translateField(field: ProductField): void {
        pendingField.value = field
        const state = fieldState(activeLanguage.value, field)
        if (state && state.origin !== 'ai') {
            confirmOverwrite.value = true
            return
        }
        void runPendingField()
    }

    async function runPendingField(): Promise<void> {
        const field = pendingField.value
        confirmOverwrite.value = false
        pendingField.value = null
        if (!field || activeLanguage.value === 'source') return
        await translateInTab(field, [field])
    }

    // The product as the form has it, for the language check.
    // For saved products, core ignored the submitted product preset and checked the saved database row; that could race the asynchronous product preset save and produce random warning on same selected product preset.
    // Language checks now send id: -1, making core build the check from the current form’s selected product preset and report IDs.
    const productPayload = () => ({
        ...product.value,
        id: -1,
        product_preset_id: selectedProductPreset.value?.id ?? product.value.product_preset_id,
        report_items: reportItems.value.map((item) => ({ id: item.id }))
    })

    async function fetchLanguageCheck(language: string | null): Promise<LanguageCheck | null> {
        if (!language || !(selectedProductPreset.value?.id ?? product.value.product_preset_id)) return null
        try {
            const response = (await checkProductLanguage(productPayload(), language)) as { data?: LanguageCheck }
            return response.data ?? null
        } catch (error: unknown) {
            console.error('Language check failed:', error)
            return null
        }
    }

    // A check answers for one language, product preset and set of reports. Once any of them
    // changes, the last answer is neither shown nor acted on: it would name the previous
    // product preset's templates or the previous tab's outdated translations.
    const checkKey = computed<string>(() =>
        JSON.stringify([renderLanguage.value, selectedProductPreset.value?.id ?? null, reportItems.value.map((item) => item.id)])
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
    // The description (of the open tab) is the one citing "value" (index 0) of the form.
    const description = {
        get value(): string {
            return descriptionModel.value
        },
        set value(text: unknown) {
            descriptionModel.value = String(text ?? '')
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
    const requiredRule = (value: unknown): true | string => !!value || t('common.required')

    // Computed properties
    const canModify = computed(() => {
        if (!isEditMode.value) return true
        return checkPermission('PUBLISH_UPDATE') && canModifyFlag.value
    })

    // The deliveries that send the product somewhere; a format without a channel is only previewed.
    const channelDeliveries = computed<Delivery[]>(() =>
        (selectedProductPreset.value?.deliveries || []).filter((delivery) => delivery.publishing_channel_id)
    )

    // The product preset's formats, in delivery order.
    const formats = computed(() => {
        const byId = new Map<number, { id: number; title: string }>()
        for (const delivery of selectedProductPreset.value?.deliveries || []) {
            if (!byId.has(delivery.product_format_id)) {
                byId.set(delivery.product_format_id, { id: delivery.product_format_id, title: delivery.product_format_title })
            }
        }
        return [...byId.values()]
    })

    const canPublish = computed(() => {
        if (channelDeliveries.value.length === 0) return false
        if (!isEditMode.value) return true
        return checkPermission('PUBLISH_PRODUCT') && canAccessFlag.value
    })

    // True when the product's current state is a FINAL state (e.g. published),
    // so newly-added non-final reports will be auto-completed by the backend cascade.
    const productStateIsFinal = computed(() => {
        if (product.value.state_id === undefined || product.value.state_id === null) return false
        return availableStates.value.some((s) => s.id === product.value.state_id && s.state_type === 'final')
    })

    const FIRST_STRONG_ISOLATE = '\u2068'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'
    const isolateAuto = (value: string): string => `${FIRST_STRONG_ISOLATE}${value}${POP_DIRECTIONAL_ISOLATE}`
    const listOf = (values: string[]): string => formatList(values.map(isolateAuto), { style: 'long', type: 'conjunction' })

    // The language a delivery renders the product in: its own, else the product's.
    const deliveryLanguage = (delivery: Delivery): string | null => delivery.language ?? product.value.language

    const deliveryLabel = (delivery: Delivery): string => {
        const label = t('product.delivery', {
            format: isolateAuto(delivery.product_format_title),
            channel: isolateAuto(String(delivery.publishing_channel_name ?? ''))
        })
        const language = deliveryLanguage(delivery)
        return language ? t('product.delivery_in_language', { language: isolateAuto(languageName(language)), delivery: label }) : label
    }

    // The deliveries Publish will send to; the confirmation dialog lists one per line.
    const tickedDeliveries = computed(() => channelDeliveries.value.filter((delivery) => tickedDeliveryIds.value.includes(delivery.id)))

    // Where the published product also appears, as the product preset sets it.
    const publicWebNote = computed(() => {
        const productPreset = selectedProductPreset.value
        if (!productPreset?.public_web_enabled) return ''
        const webs = productPreset.public_web_names || []
        return webs.length > 0 ? t('product.public_web_some', { webs: listOf(webs) }) : t('product.public_web_all')
    })

    // The webs the product can appear on, its product preset's; it can be left out of some.
    const webChoices = computed(() => (selectedProductPreset.value?.public_web_enabled ? selectedProductPreset.value.web_choices || [] : []))

    // Those it appears on: every one unless it is limited to some, or kept off them all. All of them
    // are stored as none, so that a web the product preset gains later shows the product too.
    const shownWebIds = computed<number[]>({
        get: () => {
            if (product.value.public_web_enabled === false) return []
            const choices = webChoices.value.map((web) => web.id)
            const own = product.value.public_web_ids || []
            return own.length > 0 ? choices.filter((id) => own.includes(id)) : choices
        },
        set: (ids) => {
            product.value.public_web_enabled = ids.length > 0
            product.value.public_web_ids =
                ids.length === 0 || ids.length === webChoices.value.length
                    ? []
                    : webChoices.value.map((web) => web.id).filter((id) => ids.includes(id))
            handleUpdateRecord()
        }
    })

    // Methods
    function resetForm() {
        product.value = {
            id: -1,
            title: '',
            description: '',
            product_preset_id: undefined,
            state_id: undefined,
            report_items: [],
            links: [],
            // Written in the user's default language unless they pick another one.
            language: defaultContentLanguage.value,
            translations: {},
            tag_ids: [],
            public_web_ids: [],
            public_web_enabled: true
        }
        resetLanguages()
        productLinks.value = []
        selectedProductPreset.value = null
        tickedDeliveryIds.value = []
        isEditMode.value = false
        showError.value = false
        canModifyFlag.value = false
        canAccessFlag.value = false
        reportItems.value = []
        formRef.value?.reset?.()
        selectDefaultState()
        initialFormState.value = snapshotForm()
    }

    function snapshotForm() {
        // The ticked deliveries are not part of the product, so they are not an unsaved change.
        return JSON.stringify({
            product: product.value,
            links: productLinks.value,
            reportItems: reportItems.value
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

    // ---- reports changed while the product is open ----
    // A report opened from here (or changed by somebody else) shows its new name, language,
    // translation status and tags on its card; the product itself does not change.
    const reportsToRefresh = new Set<string>()
    let reportRefreshTimer: ReturnType<typeof setTimeout> | null = null

    const onReportItemUpdated = (event: Event): void => {
        const id = (event as CustomEvent<{ report_item_id?: number | string }>).detail?.report_item_id
        if (!visible.value || id === undefined || id === null) return
        if (!reportItems.value.some((item) => String(item.id) === String(id))) return
        reportsToRefresh.add(String(id))
        // Typing in a report sends an update per field: refresh once it settles.
        if (reportRefreshTimer) clearTimeout(reportRefreshTimer)
        reportRefreshTimer = setTimeout(() => void refreshChangedReports(), 500)
    }

    type ReportDetail = {
        title?: string
        title_prefix?: string
        language?: string | null
        last_updated?: string
        tags?: number[]
        translation_status?: Record<string, string>
        translations?: Record<string, Record<string, { value?: string }>>
    }

    // What a report's card shows, from the report's detail (a product not saved yet has no stored list).
    const cardFieldsOf = (detail: ReportDetail): Record<string, unknown> => {
        const fields: Record<string, unknown> = {
            title: detail.title,
            title_prefix: detail.title_prefix,
            language: detail.language ?? null,
            last_updated: detail.last_updated,
            tags: detail.tags ?? [],
            translation_status: detail.translation_status ?? {},
            title_translations: Object.fromEntries(
                Object.entries(detail.translations ?? {}).map(([language, texts]) => [
                    language,
                    Object.fromEntries(Object.entries(texts).map(([field, state]) => [field, state?.value ?? '']))
                ])
            )
        }
        return Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined))
    }

    async function refreshChangedReports(): Promise<void> {
        reportRefreshTimer = null
        const ids = new Set(reportsToRefresh)
        reportsToRefresh.clear()
        if (ids.size === 0) return
        try {
            const fresh = new Map<string, Record<string, unknown>>()
            if (product.value.id !== -1) {
                const response = await getProductById(product.value.id)
                for (const item of (response.data?.report_items || []) as ReportItem[]) {
                    if (ids.has(String(item.id))) fresh.set(String(item.id), item)
                }
            } else {
                for (const id of ids) fresh.set(id, cardFieldsOf((await getReportItem(id)).data as ReportDetail))
            }
            // The report's change is not an edit of the product: keep a pristine form pristine.
            const wasPristine = !hasUnsavedChanges()
            reportItems.value = reportItems.value.map((item) => {
                const update = fresh.get(String(item.id))
                return update ? { ...item, ...update } : item
            })
            if (wasPristine) initialFormState.value = snapshotForm()
            // What the notices said about these reports (their language, translations) may be over.
            languageCheck.value = null
            if (visible.value) void loadCurrentCheck()
        } catch (error: unknown) {
            console.error('Failed to refresh the reports of the product:', error)
        }
    }

    function selectDefaultState() {
        if (!availableStates.value || availableStates.value.length === 0) return
        const defaultState = availableStates.value.find((state) => state.is_default)
        if (defaultState) {
            product.value.state_id = defaultState.id
        }
    }

    // Every channel of the product preset is ticked to begin with.
    function tickAllDeliveries(): void {
        tickedDeliveryIds.value = channelDeliveries.value.map((delivery) => delivery.id)
    }

    // The product's product preset, once both the product and the user's product presets are loaded.
    function syncSelectedProductPreset(): void {
        const productPresetId = product.value.product_preset_id
        if (productPresetId === undefined || selectedProductPreset.value?.id === productPresetId) return
        selectedProductPreset.value = productPresets.value.find((productPreset) => productPreset.id === productPresetId) || null
        tickAllDeliveries()
    }

    function handleProductPresetChange(): void {
        if (selectedProductPreset.value) {
            product.value.product_preset_id = selectedProductPreset.value.id
            // Webs picked from another product preset's: on every web of this one.
            product.value.public_web_ids = []
            product.value.public_web_enabled = true
            tickAllDeliveries()
            handleUpdateRecord()
        }
    }

    async function prepareProduct(): Promise<boolean> {
        const { valid } = (await formRef.value?.validate?.()) || { valid: false }
        if (!valid) return false

        showError.value = false
        product.value.product_preset_id = selectedProductPreset.value?.id ?? product.value.product_preset_id
        product.value.report_items = reportItems.value.map((item) => ({ id: item.id }))
        product.value.links = productLinks.value
            .map((link) => ({ key: String(link.value_description ?? ''), url: String(link.value ?? '').trim() }))
            .filter((link) => link.url)
        return true
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

    function validateDeliverySelection(): boolean {
        if (tickedDeliveries.value.length === 0) {
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.no_delivery_selected' }
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

    /** A language's check, with only the formats the ticked deliveries send in that language. */
    function publishCheckFor(language: string, check: LanguageCheck | null): LanguageCheck | null {
        if (!check) return null
        const formatIds = new Set(
            tickedDeliveries.value.filter((delivery) => deliveryLanguage(delivery) === language).map((delivery) => delivery.product_format_id)
        )
        return { ...check, formats: check.formats.filter((format) => formatIds.has(format.product_format_id)) }
    }

    // Counts the confirmations opened, so a check that arrives late fills only its own.
    let publishCheckRun = 0

    async function handlePublishConfirmation(): Promise<void> {
        if (!validateDeliverySelection()) return

        const run = ++publishCheckRun
        const languages = [...new Set(tickedDeliveries.value.map(deliveryLanguage).filter((language): language is string => !!language))]
        // The open tab's language is usually checked already.
        publishChecks.value = languages.map((language) => ({
            language,
            check: language === renderLanguage.value ? publishCheckFor(language, currentCheck.value) : null
        }))
        if (!isEditMode.value && hasUnsavedChanges()) {
            showPublishUnsavedConfirmation.value = true
        } else {
            showPublishConfirmation.value = true
        }
        // The other checks: the dialog lists each once it arrives.
        for (const [index, entry] of publishChecks.value.entries()) {
            if (entry.check) continue
            const check = entry.language === renderLanguage.value ? await loadCurrentCheck() : await fetchLanguageCheck(entry.language)
            if (run !== publishCheckRun) return
            publishChecks.value = publishChecks.value.map((other, at) =>
                at === index ? { ...other, check: publishCheckFor(other.language, check) } : other
            )
        }
    }

    async function handlePublish(): Promise<void> {
        showPublishConfirmation.value = false

        if (!(await prepareProduct())) return

        const deliveries = tickedDeliveries.value

        try {
            const response = await publishProduct(
                product.value,
                deliveries.map((delivery) => delivery.id)
            )
            notifyPublishResults(response.data?.results || [], deliveries)
        } catch (error: unknown) {
            // A failing delivery answers 500 with the result of every delivery.
            const results = (error as { response?: { data?: { results?: PublishResult[] } } }).response?.data?.results
            if (results) {
                notifyPublishResults(results, deliveries)
                return
            }
            showError.value = true
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'product.publish_error' }
                })
            )
        }
    }

    /** Say whether every delivery went out, or which did not. One core no longer has is not reported, so did not go out. */
    function notifyPublishResults(results: PublishResult[], deliveries: Delivery[]): void {
        const sentIds = new Set(results.filter((result) => result.success).map((result) => result.delivery_id))
        const failed = deliveries.filter((delivery) => !sentIds.has(delivery.id))
        const detail =
            failed.length === 0
                ? { type: 'success', loc: 'product.publish_successful' }
                : { type: 'error', loc: 'product.publish_failed_deliveries', params: { deliveries: listOf(failed.map(deliveryLabel)) } }
        window.dispatchEvent(new CustomEvent('notification', { detail }))
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

    async function handlePreview(event?: MouseEvent, productFormatId?: number): Promise<void> {
        if (needsOutdatedConfirmation(currentCheck.value, () => void handlePreview(event, productFormatId))) return
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

            const response = await previewProduct(product.value, ctrl, authStore.jwt, productFormatId, renderLanguage.value)
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

    async function handleDownload(event?: MouseEvent, productFormatId?: number): Promise<void> {
        if (needsOutdatedConfirmation(await loadCurrentCheck(), () => void handleDownload(event, productFormatId))) return
        const ctrl = Boolean(event?.ctrlKey || event?.metaKey)

        if (!(await prepareProduct())) return

        try {
            const response = await previewProduct(product.value, ctrl, authStore.jwt, productFormatId, renderLanguage.value)
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

    async function loadProductPresets() {
        try {
            const response = await getAllUserProductPresets()
            productPresets.value = (response.data.items as ProductPreset[]) || []
            syncSelectedProductPreset()
        } catch (error: unknown) {
            console.error('Failed to load product presets:', error)
        }
    }

    // Public methods for opening dialog
    function openDialog(): void {
        visible.value = true
        resetForm()
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
            product_preset_id: data.product_preset_id,
            state_id: data.state_id,
            report_items: data.report_items || [],
            links: data.links || [],
            language: (data as ProductDetailPayload).language ?? null,
            translations: Object.fromEntries(
                Object.entries((data as ProductDetailPayload).translations ?? {}).map(([language, states]) => [
                    language,
                    Object.fromEntries(
                        PRODUCT_FIELDS.filter((field) => states[field]?.value).map((field) => [
                            field,
                            { value: String(states[field]?.value), origin: states[field]?.origin ?? 'manual' }
                        ])
                    )
                ])
            ),
            tag_ids: (data as ProductDetailPayload).tags ?? [],
            public_web_ids: (data as ProductDetailPayload).public_web_ids,
            public_web_enabled: (data as ProductDetailPayload).public_web_enabled
        }
        resetLanguages()
        storedTranslations.value = Object.fromEntries(
            Object.entries((data as ProductDetailPayload).translations ?? {}).map(([language, states]) => [
                language,
                Object.fromEntries(
                    PRODUCT_FIELDS.filter((field) => states[field]).map((field) => [
                        field,
                        { ...states[field]!, original: String(data[field] ?? '') }
                    ])
                )
            ])
        )
        productLinks.value = toLinkValues(data.links)

        reportItems.value = Array.isArray(data.report_items) ? [...data.report_items] : []
        selectedProductPreset.value = null
        syncSelectedProductPreset()
        initialFormState.value = snapshotForm()
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
        loadProductPresets()
        window.addEventListener('new-product', handleNewProduct)
        window.addEventListener('show-product-edit', handleShowProductEdit)
        window.addEventListener('report-item-updated', onReportItemUpdated)
    })

    onUnmounted(() => {
        window.removeEventListener('new-product', handleNewProduct)
        window.removeEventListener('show-product-edit', handleShowProductEdit)
        window.removeEventListener('report-item-updated', onReportItemUpdated)
        if (reportRefreshTimer) clearTimeout(reportRefreshTimer)
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

    .publish-deliveries {
        list-style: none;
        padding-inline-start: 16px;
    }
</style>
