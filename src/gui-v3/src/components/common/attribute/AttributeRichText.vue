<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <div v-if="readOnly || values[index].remote" class="richtext-display pa-3 rounded">
          <div v-html="sanitizeHtml(values[index].value)" />
        </div>

        <!-- Editable -->
        <AttributeValueLayout
          v-if="!readOnly && canModify && !values[index].remote"
          :del-button="true"
          :occurrence="attributeGroup.min_occurrence"
          :values="values"
          :val-index="index"
          @del-value="del(index)"
        >
          <template #col_middle>
            <Editor
              v-model="values[index].value"
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

<script setup>
import Editor from 'primevue/editor'
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'
import { useAttributes } from './useAttributes.js'

const props = defineProps({
  attributeGroup: {
    type: Object,
    required: true
  },
  values: {
    type: Array,
    required: true
  },
  readOnly: {
    type: Boolean,
    default: false
  },
  edit: {
    type: Boolean,
    default: false
  },
  modify: {
    type: Boolean,
    default: false
  },
  reportItemId: {
    type: Number,
    required: true
  }
})

const { canModify, addButtonVisible, add, del, onBlur } = useAttributes(props)

// Basic HTML sanitization - removes potentially dangerous tags/attributes
const sanitizeHtml = (html) => {
  if (!html) return ''
  try {
    // Create a temporary element to parse HTML
    const temp = document.createElement('div')
    temp.innerHTML = html

    // List of allowed HTML tags for rich text
    const allowedTags = ['p', 'br', 'b', 'i', 'u', 's', 'em', 'strong', 'span', 'div', 'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'code']
    const allowedAttrs = ['class', 'style', 'href', 'target', 'rel']

    // Walk through all nodes and remove unsafe ones
    const walk = (node) => {
      const nodesToRemove = []
      for (let i = 0; i < node.childNodes.length; i++) {
        const child = node.childNodes[i]
        if (child.nodeType === 1) { // Element node
          const tagName = child.tagName.toLowerCase()

          if (!allowedTags.includes(tagName)) {
            // Keep content but remove the tag
            while (child.childNodes.length) {
              node.insertBefore(child.childNodes[0], child)
            }
            nodesToRemove.push(child)
          } else {
            // Remove unsafe attributes
            const attrs = child.attributes
            for (let j = attrs.length - 1; j >= 0; j--) {
              if (!allowedAttrs.includes(attrs[j].name)) {
                child.removeAttribute(attrs[j].name)
              }
            }
            // Sanitize href to prevent javascript: URLs
            if (child.href && child.href.startsWith('javascript:')) {
              child.removeAttribute('href')
            }
            walk(child)
          }
        }
      }
      nodesToRemove.forEach(node => node.parentNode.removeChild(node))
    }

    walk(temp)
    return temp.innerHTML
  } catch (error) {
    // Fallback: return text with tags stripped
    return html.replace(/<[^>]*>/g, '')
  }
}

// Count words in rich text (strips HTML)
const getWordCount = (html) => {
  if (!html) return 0
  const text = html.replace(/<[^>]*>/g, '').trim()
  return text.split(/\s+/).filter(w => w.length > 0).length
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
