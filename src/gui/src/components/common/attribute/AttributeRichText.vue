<template>
    <AttributeItemLayout
        :add-button="addButtonVisible"
        :values="values"
        @add-value="add"
    >
        <template #content>
            <div
                v-for="(value, index) in values"
                :key="`${value.index}-${index}`"
                class="value-holder"
            >
                <!-- Read-only or remote -->
                <div
                    v-if="readOnly || value.remote"
                    class="richtext-display pa-3 rounded"
                >
                    <div v-html="sanitizeRichTextHtml(numberCitations(value.value))" />
                </div>

                <!-- Editable -->
                <AttributeValueLayout
                    v-if="!readOnly && canModify && !value.remote"
                    :del-button="true"
                    :occurrence="attributeGroup.min_occurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="del(index)"
                >
                    <template #col_middle>
                        <RichTextEditor
                            :ref="(editor) => setEditor(index, editor)"
                            v-model="value.value"
                            :placeholder="t('report_item.enter_rich_text')"
                            :citations="references.enabled ? citations : null"
                            @focus="onFocus(index)"
                            @blur="onBlur(index)"
                            @keyup="onKeyUp(index)"
                        >
                            <template
                                v-if="references.enabled"
                                #toolbar-append
                            >
                                <CiteMenu
                                    :links="references.links.value"
                                    :disabled="value.locked || !canModify"
                                    density="comfortable"
                                    size="small"
                                    @pick="(link) => cite(index, link.key)"
                                />
                            </template>
                        </RichTextEditor>
                        <ReferencePreview
                            v-if="references.enabled"
                            :text="value.value"
                            :resolve="references.resolve"
                        />
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import RichTextEditor from '@/components/common/RichTextEditor.vue'
    import CiteMenu from '@/components/common/links/CiteMenu.vue'
    import ReferencePreview from '@/components/common/links/ReferencePreview.vue'
    import { useLinkReferences } from '@/composables/useLinkReferences'
    import { LINK_TOKEN_RE, linkToken } from '@/utils/linkReferences'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { useAttributes } from './useAttributes'
    import { sanitizeRichTextHtml } from '@/utils/sanitizeRichTextHtml'
    import { useI18n } from 'vue-i18n'

    type AttributeValueItem = {
        index?: string | number
        value: string
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = {
        min_occurrence?: number
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttributeValueItem[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number | null
        }>(),
        {
            readOnly: false,
            edit: false,
            modify: false
        }
    )

    const { canModify, addInitialValues, addButtonVisible, add, del, onFocus, onBlur, onKeyUp, onEdit } = useAttributes(props)
    const { t } = useI18n()
    const references = useLinkReferences()

    const citations = computed(() => new Map(references.links.value.map((link) => [link.key, link])))

    // The editors by value index, to insert citations at their cursor.
    const editors = new Map<number, { insertText: (text: string) => void }>()
    const setEditor = (index: number, editor: unknown): void => {
        if (editor && typeof (editor as { insertText?: unknown }).insertText === 'function') {
            editors.set(index, editor as { insertText: (text: string) => void })
        } else {
            editors.delete(index)
        }
    }

    /** Insert a citation at the editor's cursor, and save it right away. */
    const cite = async (index: number, key: string): Promise<void> => {
        editors.get(index)?.insertText(linkToken(key))
        // Saved now rather than on blur: the focus may move into the menu and back, and a blur
        // seen before the insertion must not be what decides whether the text changed.
        await onEdit(index)
    }

    /** Read-only text shows the numbers of the cited links (digits only, so safe in the HTML). */
    const numberCitations = (html: string | null | undefined): string =>
        (html || '').replace(LINK_TOKEN_RE, (_token, key: string) => {
            const link = references.resolve(key)
            return link ? `[${link.number}]` : '[?]'
        })

    // Count words in rich text (strips HTML)
    const getWordCount = (html: string | null | undefined): number => {
        if (!html) return 0
        const text = html.replace(/<[^>]*>/g, '').trim()
        return text.split(/\s+/).filter((w) => w.length > 0).length
    }

    onMounted(addInitialValues)
</script>

<style scoped>
    .line-clamp-4 {
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
</style>
