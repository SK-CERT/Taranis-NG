<template>
    <div class="attribute-link w-100 ps-2 pe-4 pt-2">
        <LinkListEditor
            :values="values"
            :read-only="readOnly"
            :disabled="!canModify"
            :min-occurrence="attributeGroup.min_occurrence ?? 0"
            :max-occurrence="attributeGroup.max_occurrence ?? null"
            :citation-count="references.citationCount"
            @insert="insertAt"
            @remove="del"
            @move="move"
            @focus="onFocus"
            @blur="onBlur"
            @keyup="onKeyUp"
        >
            <template #actions>
                <v-menu
                    v-if="references.enabled && canModify && references.newsItemLinks.value.length > 0"
                    location="bottom end"
                >
                    <template #activator="{ props: menuProps }">
                        <v-btn
                            v-bind="menuProps"
                            variant="flat"
                            size="small"
                            :prepend-icon="ICONS.NEWSPAPER_PLUS"
                            :disabled="newsItemLinks.length === 0 || !canAdd"
                            :title="newsItemLinks.length === 0 ? t('links.no_news_item_links') : t('links.from_news_items')"
                            data-test="link-from-news-items"
                        >
                            {{ t('links.from_news_items') }}
                        </v-btn>
                    </template>
                    <v-list
                        density="compact"
                        max-width="560"
                    >
                        <v-list-item
                            v-if="newsItemLinks.length > 1"
                            :prepend-icon="ICONS.PLUS"
                            :title="t('links.add_all')"
                            data-test="link-from-news-items-all"
                            @click="addLinks(newsItemLinks)"
                        />
                        <v-list-item
                            v-for="url in newsItemLinks"
                            :key="url"
                            :title="url"
                            data-test="link-from-news-item"
                            @click="addLinks([url])"
                        />
                    </v-list>
                </v-menu>
            </template>
        </LinkListEditor>
    </div>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import LinkListEditor from '@/components/common/links/LinkListEditor.vue'
    import { useLinkReferences } from '@/composables/useLinkReferences'
    import { ICONS } from '@/config/ui-constants'
    import { useAttributes } from './useAttributes'

    type AttributeValueItem = {
        index?: string | number
        value: string | null
        value_description?: string
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = {
        min_occurrence?: number
        max_occurrence?: number | null
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

    const { t } = useI18n()
    const references = useLinkReferences()

    const { canModify, addInitialValues, add, del, onFocus, onBlur, onKeyUp, onEdit, move } = useAttributes(props)

    const canAdd = computed(() => props.values.length < (props.attributeGroup.max_occurrence ?? Infinity))

    // News item sources that are not among the links yet.
    const newsItemLinks = computed(() => {
        const present = new Set(props.values.map((value) => String(value.value ?? '').trim()))
        return references.newsItemLinks.value.filter((url) => !present.has(url))
    })

    /** Add a link at `index`: appended first (that is what the backend can do), then moved up. */
    const insertAt = async (index: number): Promise<void> => {
        const before = props.values.length
        await add()
        if (props.values.length === before) return
        const last = props.values.length - 1
        if (index < last) {
            await move(last, index)
        }
    }

    /** Add the URLs as links, filling empty rows (like the one a required attribute starts with) first. */
    const addLinks = async (urls: string[]): Promise<void> => {
        for (const url of urls) {
            let index = props.values.findIndex((value) => !String(value.value ?? '').trim() && value.locked !== true)
            if (index === -1) {
                const before = props.values.length
                if (!canAdd.value) return
                await add()
                if (props.values.length === before) return
                index = props.values.length - 1
            }
            const value = props.values[index]
            if (!value) return
            value.value = url
            await onEdit(index)
        }
    }

    onMounted(addInitialValues)
</script>
