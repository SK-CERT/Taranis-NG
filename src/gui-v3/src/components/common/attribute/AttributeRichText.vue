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
                    <div v-html="sanitizeHtml(value.value)" />
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
    import Editor from 'primevue/editor'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { useAttributes } from './useAttributes'

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

    const { canModify, addButtonVisible, add, del, onBlur } = useAttributes(props)

    // Basic HTML sanitization - removes potentially dangerous tags/attributes
    const sanitizeHtml = (html: string | null | undefined): string => {
        if (!html) return ''
        try {
            // Create a temporary element to parse HTML
            const temp = document.createElement('div')
            temp.innerHTML = html

            // List of allowed HTML tags for rich text
            const allowedTags = [
                'p',
                'br',
                'b',
                'i',
                'u',
                's',
                'em',
                'strong',
                'span',
                'div',
                'ul',
                'ol',
                'li',
                'a',
                'h1',
                'h2',
                'h3',
                'h4',
                'h5',
                'h6',
                'blockquote',
                'pre',
                'code'
            ]
            const allowedAttrs = ['class', 'style', 'href', 'target', 'rel']

            // Walk through all nodes and remove unsafe ones
            const walk = (node: Node): void => {
                const nodesToRemove: Node[] = []
                for (let i = 0; i < node.childNodes.length; i++) {
                    const child = node.childNodes[i]
                    if (!child) {
                        continue
                    }
                    if (child.nodeType === 1) {
                        // Element node
                        const element = child as Element
                        const tagName = element.tagName.toLowerCase()

                        if (!allowedTags.includes(tagName)) {
                            // Keep content but remove the tag
                            while (child.childNodes.length) {
                                const firstChild = child.childNodes[0]
                                if (!firstChild) {
                                    break
                                }
                                node.insertBefore(firstChild as Node, child)
                            }
                            nodesToRemove.push(child)
                        } else {
                            // Remove unsafe attributes
                            const attrs = element.attributes
                            for (let j = attrs.length - 1; j >= 0; j--) {
                                const attr = attrs[j]
                                if (!attr) {
                                    continue
                                }
                                if (!allowedAttrs.includes(attr.name)) {
                                    element.removeAttribute(attr.name)
                                }
                            }
                            // Sanitize href to prevent javascript: URLs
                            const href = element.getAttribute('href')
                            if (href && href.startsWith('javascript:')) {
                                element.removeAttribute('href')
                            }
                            walk(element)
                        }
                    }
                }
                nodesToRemove.forEach((childNode) => childNode.parentNode?.removeChild(childNode))
            }

            walk(temp)
            return temp.innerHTML
        } catch {
            // Fallback: return text with tags stripped
            return html.replace(/<[^>]*>/g, '')
        }
    }

    // Count words in rich text (strips HTML)
    const getWordCount = (html: string | null | undefined): number => {
        if (!html) return 0
        const text = html.replace(/<[^>]*>/g, '').trim()
        return text.split(/\s+/).filter((w) => w.length > 0).length
    }
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
