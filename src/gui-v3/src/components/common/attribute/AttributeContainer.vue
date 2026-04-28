<template>
  <!-- Dynamic component dispatcher - renders the appropriate attribute type -->
  <component
    :is="attributeComponent"
    v-if="attributeComponent"
    :attribute-group="attributeItem.attribute_group_item"
    :values="attributeItem.values || []"
    :read-only="readOnly"
    :edit="edit"
    :modify="modify"
    :report-item-id="reportItemId"
  />
</template>

<script setup>
import { computed } from 'vue'

// Lazy load attribute components to reduce bundle size
import AttributeString from './AttributeString.vue'
import AttributeNumber from './AttributeNumber.vue'
import AttributeBoolean from './AttributeBoolean.vue'
import AttributeEnum from './AttributeEnum.vue'
import AttributeRadio from './AttributeRadio.vue'
import AttributeText from './AttributeText.vue'
import AttributeDate from './AttributeDate.vue'

// Phase 2 components (ready to enable)
import AttributeTime from './AttributeTime.vue'
import AttributeDateTime from './AttributeDateTime.vue'
import AttributeRichText from './AttributeRichText.vue'
import AttributeTLP from './AttributeTLP.vue'
import AttributeAttachment from './AttributeAttachment.vue'

// Phase 3 components (now enabled)
import AttributeCPE from './AttributeCPE.vue'
import AttributeCVE from './AttributeCVE.vue'
import AttributeCWE from './AttributeCWE.vue'
import AttributeCVSS from './AttributeCVSS.vue'

const props = defineProps({
  attributeItem: {
    type: Object,
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

// Map attribute types to components
const componentMap = {
  // Phase 1 - Core types (DONE)
  STRING: AttributeString,
  NUMBER: AttributeNumber,
  BOOLEAN: AttributeBoolean,
  ENUM: AttributeEnum,
  RADIO: AttributeRadio,
  TEXT: AttributeText,
  DATE: AttributeDate,

  // Phase 2 - Common types (Ready to use)
  TIME: AttributeTime,
  DATE_TIME: AttributeDateTime,
  RICH_TEXT: AttributeRichText,
  TLP: AttributeTLP,
  ATTACHMENT: AttributeAttachment,

  // Phase 3 - Advanced types (Now enabled)
  CPE: AttributeCPE,
  CVE: AttributeCVE,
  CWE: AttributeCWE,
  CVSS: AttributeCVSS
}

const attributeComponent = computed(() => {
  const attrType = props.attributeItem.attribute_group_item.attribute.type
  return componentMap[attrType] || null
})
</script>
