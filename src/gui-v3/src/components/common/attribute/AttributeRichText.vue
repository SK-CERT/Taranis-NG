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
                    <div v-html="sanitizeRichTextHtml(value.value)" />
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
                        <Editor
                            v-model="value.value"
                            :read-only="false"
                            theme="snow"
                            placeholder="Enter rich text..."
                            style="height: 250px"
                            @blur="onBlur(index)"
                        />
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import { onMounted } from 'vue'
    import Editor from 'primevue/editor'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { useAttributes } from './useAttributes'
    import { sanitizeRichTextHtml } from '@/utils/sanitizeRichTextHtml'

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

    const { canModify, addInitialValues, addButtonVisible, add, del, onBlur } = useAttributes(props)

    // Count words in rich text (strips HTML)
    const getWordCount = (html: string | null | undefined): number => {
        if (!html) return 0
        const text = html.replace(/<[^>]*>/g, '').trim()
        return text.split(/\s+/).filter((w) => w.length > 0).length
    }

    onMounted(addInitialValues)
</script>

<style scoped>
    /* Rich text editor styling */
    :deep(.p-editor) {
        border-radius: 4px;
    }

    :deep(.ql-editor) {
        min-height: 250px;
    }

    .prose {
        color: var(--p-text-color);
    }

    .line-clamp-4 {
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
</style>
